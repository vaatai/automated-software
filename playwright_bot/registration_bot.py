"""Registration bot — drives multi-step form filling using BrowserManager sessions.

Integrates centralized error handling for:
  - Screenshot + HTML snapshot capture on every failure
  - Browser console + network request logging
  - CAPTCHA detection, selector change detection
  - Cloudflare challenge detection
  - OTP timeout tracking
  - Proxy ban detection
  - Rich ErrorContext for post-mortem debugging
  - Detailed step-by-step logging
  - Playwright tracing support
"""

import logging
import time

from otp.fivesim_service import FiveSimService
from otp.mailslurp_service import MailSlurpService
from otp.pvapins_service import PVAPinsService
from playwright_bot.browser_manager import BrowserManager, BrowserSession
from utils.data_generator import generate_registration_data
from utils.error_handler import ErrorCategory, ErrorContext, ErrorHandler
from utils.failure_detectors import (
    CaptchaDetector,
    OTPTimeoutDetector,
    ProxyBanDetector,
    SelectorChangeDetector,
)

logger = logging.getLogger(__name__)

# Default timeouts (ms)
NAVIGATION_TIMEOUT = 30_000
ELEMENT_TIMEOUT = 10_000
OTP_ELEMENT_TIMEOUT = 15_000

# Cloudflare challenge-specific indicators (must match ≥2 to trigger)
CLOUDFLARE_CHALLENGE_INDICATORS = [
    "cf-browser-verification",
    "cf_chl_opt",
    "challenge-platform",
    "_cf_chl",
    "please wait while we verify",
    "verify you are human",
    "checking your browser",
]

# Title-only indicators (a single match in the page title is sufficient)
CLOUDFLARE_TITLE_INDICATORS = [
    "just a moment",
    "attention required",
]


class RegistrationBot:
    """Headless Playwright bot that automates website registration.

    Uses :class:`BrowserManager` for isolated contexts with stealth,
    fingerprint randomization, and proxy support.

    Supports the nested ``FormConfig`` schema:
        form_config.steps[]        — multi-step form filling
        form_config.otp_settings   — OTP field selectors
        form_config.captcha_settings (not yet automated)
        form_config.success_indicator

    Error handling:
        Every failure produces a rich :class:`ErrorContext` with screenshots,
        HTML snapshots, browser logs, and failure classification.
        The error context is attached to the result dict under ``error_context``.
    """

    def __init__(self, browser_manager: BrowserManager) -> None:
        self.manager = browser_manager
        self.mailslurp = MailSlurpService()
        self.fivesim = FiveSimService()
        self.pvapins = PVAPinsService()

        # Failure detectors
        self._captcha_detector = CaptchaDetector()
        self._selector_detector = SelectorChangeDetector()
        self._proxy_ban_detector = ProxyBanDetector()

    async def register(
        self,
        website_config: dict,
        registration_id: int,
        requires_email_otp: bool = False,
        requires_mobile_otp: bool = False,
        custom_data: dict | None = None,
        proxy: dict | None = None,
        attempt_number: int = 1,
    ) -> dict:
        """Execute a full registration flow inside an isolated browser session.

        Returns a result dict. On failure, ``result["error_context"]`` contains
        a serialized :class:`ErrorContext` with full debugging information.
        """
        error_handler = ErrorHandler(
            registration_id=registration_id,
            attempt_number=attempt_number,
        )
        start_time = time.monotonic()

        result: dict = {
            "registration_id": registration_id,
            "status": "failed",
            "email_used": None,
            "phone_used": None,
            "username": None,
            "email_otp_verified": False,
            "mobile_otp_verified": False,
            "error": None,
            "error_context": None,
            "screenshot": None,
            "html_snapshot": None,
            "browser_log": None,
            "browser_log_json": None,
            "trace_path": None,
            "steps_completed": [],
        }
        inbox_id: str | None = None
        sms_order_id: str | None = None
        sms_provider: str | None = None

        session_id = f"reg-{registration_id}"
        logger.info(
            "[reg-%d] Starting registration (attempt=%d, email_otp=%s, mobile_otp=%s)",
            registration_id, attempt_number, requires_email_otp, requires_mobile_otp,
        )

        try:
            async with self.manager.acquire_session(session_id=session_id, proxy=proxy) as session:
                try:
                    page = session.page

                    # ── Step 0: Generate registration data ──
                    reg_data = generate_registration_data()
                    if custom_data:
                        reg_data.update(custom_data)
                    result["username"] = reg_data.get("username")
                    logger.info(
                        "[reg-%d] Generated data: username=%s",
                        registration_id, reg_data.get("username"),
                    )
                    result["steps_completed"].append("data_generated")

                    # ── Step 1: Provision temp email ──
                    if requires_email_otp:
                        logger.info("[reg-%d] Provisioning email inbox...", registration_id)
                        try:
                            inbox = await self.mailslurp.create_inbox()
                            inbox_id = inbox["inbox_id"]
                            reg_data["email"] = inbox["email_address"]
                            result["email_used"] = reg_data["email"]
                            logger.info(
                                "[reg-%d] Email provisioned: %s",
                                registration_id, reg_data["email"],
                            )
                            result["steps_completed"].append("email_provisioned")
                        except Exception as e:
                            logger.error("[reg-%d] Email provisioning failed: %s", registration_id, e)
                            result["error"] = f"Email provisioning failed: {e}"
                            result["screenshot"] = await session.screenshot("email_provision_fail")
                            return result

                    # ── Step 2: Provision phone number ──
                    if requires_mobile_otp:
                        phone_country = (custom_data or {}).get("phone_country", "US")
                        reuse_rental_id = (custom_data or {}).get("reuse_rental_id")

                        if reuse_rental_id:
                            from otp.sms_provider import RentalResult
                            reuse_phone = (custom_data or {}).get("reuse_phone", "")
                            reuse_provider = (custom_data or {}).get("reuse_provider", "5sim")
                            reuse_order_id = (custom_data or {}).get("reuse_order_id", "")
                            sms_provider = reuse_provider
                            sms_order_id = reuse_order_id
                            reg_data["phone"] = reuse_phone
                            result["phone_used"] = reuse_phone
                            logger.info(
                                "[reg-%d] Reusing rental #%s phone=%s",
                                registration_id, reuse_rental_id, reuse_phone,
                            )
                        else:
                            logger.info(
                                "[reg-%d] Renting phone number (country=%s)...",
                                registration_id, phone_country,
                            )
                            try:
                                num = await self.fivesim.rent_number(country=phone_country)
                                sms_provider = "5sim"
                            except Exception as e5:
                                logger.warning(
                                    "[reg-%d] 5SIM failed (%s), trying PVAPins...",
                                    registration_id, e5,
                                )
                                try:
                                    num = await self.pvapins.rent_number(country=phone_country)
                                    sms_provider = "pvapins"
                                except Exception as ep:
                                    logger.error(
                                        "[reg-%d] All SMS providers failed: 5sim=%s pvapins=%s",
                                        registration_id, e5, ep,
                                    )
                                    result["error"] = f"SMS providers failed: 5sim={e5}, pvapins={ep}"
                                    result["screenshot"] = await session.screenshot("sms_fail")
                                    return result
                            sms_order_id = num.order_id
                            reg_data["phone"] = num.phone_number
                            result["phone_used"] = reg_data["phone"]
                            logger.info(
                                "[reg-%d] Phone rented: %s via %s (order=%s)",
                                registration_id, num.phone_number, sms_provider, sms_order_id,
                            )
                        result["steps_completed"].append("phone_provisioned")

                    # ── Step 3: Navigate to registration page ──
                    form_cfg = website_config.get("form_config", {})
                    url = form_cfg.get("registration_url", website_config.get("url", ""))
                    logger.info("[reg-%d] Navigating to: %s", registration_id, url)

                    try:
                        response = await page.goto(
                            url,
                            wait_until="domcontentloaded",
                            timeout=NAVIGATION_TIMEOUT,
                        )
                        status = response.status if response else "no response"
                        logger.info(
                            "[reg-%d] Navigation complete (status=%s, url=%s)",
                            registration_id, status, page.url,
                        )
                    except Exception as nav_exc:
                        logger.error(
                            "[reg-%d] Navigation failed: %s", registration_id, nav_exc,
                        )
                        result["error"] = f"Navigation failed: {nav_exc}"
                        result["screenshot"] = await session.screenshot("nav_fail")
                        result["html_snapshot"] = await session.html_snapshot("nav_fail")
                        return result

                    await page.wait_for_timeout(2000)
                    result["steps_completed"].append("navigation")

                    # Screenshot after navigation
                    await session.screenshot("after_navigation")

                    # ── Step 3a: Check for Cloudflare challenge ──
                    cloudflare_blocked = await self._detect_cloudflare(page)
                    if cloudflare_blocked:
                        logger.warning(
                            "[reg-%d] Cloudflare challenge detected! Waiting 10s...",
                            registration_id,
                        )
                        await page.wait_for_timeout(10000)
                        # Recheck after waiting
                        cloudflare_blocked = await self._detect_cloudflare(page)
                        if cloudflare_blocked:
                            elapsed_ms = int((time.monotonic() - start_time) * 1000)
                            ctx = ErrorContext(
                                registration_id=registration_id,
                                category=ErrorCategory.CAPTCHA_DETECTED,
                                error_type="CloudflareChallenge",
                                error_message="Cloudflare challenge could not be bypassed",
                                captcha_detected=True,
                                captcha_type="cloudflare",
                                step_name="cloudflare_check",
                                attempt_number=attempt_number,
                                elapsed_ms=elapsed_ms,
                            )
                            await error_handler._capture_browser_state(ctx, session)
                            error_handler._save_debug_report(ctx)
                            result["error"] = ctx.error_message
                            result["error_context"] = ctx.to_dict()
                            result["screenshot"] = ctx.screenshot_path
                            result["html_snapshot"] = ctx.html_snapshot_path
                            return result

                    # ── Step 3b: Check for CAPTCHA / proxy ban ──
                    page_check = await self._check_page_after_navigation(session, error_handler)
                    if page_check is not None:
                        logger.warning(
                            "[reg-%d] Page check failed: %s",
                            registration_id, page_check.error_message,
                        )
                        result["error"] = page_check.error_message
                        result["error_context"] = page_check.to_dict()
                        result["screenshot"] = page_check.screenshot_path
                        result["html_snapshot"] = page_check.html_snapshot_path
                        return result
                    result["steps_completed"].append("page_checks_passed")

                    # ── Step 3c: Validate selectors ──
                    selector_failures = await self._validate_selectors(page, form_cfg)
                    if selector_failures:
                        logger.warning(
                            "[reg-%d] Selector validation failed: %s",
                            registration_id, selector_failures,
                        )
                        elapsed_ms = int((time.monotonic() - start_time) * 1000)
                        ctx = ErrorContext(
                            registration_id=registration_id,
                            category=ErrorCategory.SELECTOR_CHANGED,
                            error_type="SelectorChanged",
                            error_message=f"Selectors not found: {', '.join(selector_failures)}",
                            selector_failures=selector_failures,
                            step_name="selector_validation",
                            attempt_number=attempt_number,
                            elapsed_ms=elapsed_ms,
                        )
                        await error_handler._capture_browser_state(ctx, session)
                        error_handler._save_debug_report(ctx)
                        result["error"] = ctx.error_message
                        result["error_context"] = ctx.to_dict()
                        result["screenshot"] = ctx.screenshot_path
                        result["html_snapshot"] = ctx.html_snapshot_path
                        return result
                    result["steps_completed"].append("selectors_validated")

                    # ── Step 4: Fill fields + submit ──
                    steps = form_cfg.get("steps", [])
                    if not steps:
                        logger.warning(
                            "[reg-%d] No form steps configured — form_config has empty steps",
                            registration_id,
                        )
                    for step_idx, step in enumerate(steps):
                        step_name = step.get("step_name", f"step_{step_idx}")
                        logger.info(
                            "[reg-%d] Executing step %d/%d: %s",
                            registration_id, step_idx + 1, len(steps), step_name,
                        )

                        # Screenshot before step
                        await session.screenshot(f"before_step_{step_idx}")

                        await self._execute_step(page, step, step_idx, reg_data, registration_id)

                        # Screenshot after step
                        await session.screenshot(f"after_step_{step_idx}")

                        logger.info(
                            "[reg-%d] Step %d completed, current URL: %s",
                            registration_id, step_idx + 1, page.url,
                        )

                        # Check page state after each step
                        step_check = await error_handler.check_page_state(
                            session, step=f"step_{step_idx}_submit"
                        )
                        if step_check is not None:
                            logger.warning(
                                "[reg-%d] Step %d post-check failed: %s",
                                registration_id, step_idx + 1, step_check.error_message,
                            )
                            result["error"] = step_check.error_message
                            result["error_context"] = step_check.to_dict()
                            result["screenshot"] = step_check.screenshot_path
                            return result
                        result["steps_completed"].append(f"step_{step_idx}_{step_name}")

                    # ── Step 5: Email OTP ──
                    otp_settings = form_cfg.get("otp_settings") or {}
                    if requires_email_otp and inbox_id:
                        logger.info("[reg-%d] Waiting for email OTP...", registration_id)
                        otp = await self._get_email_otp_with_tracking(inbox_id, error_handler)
                        if otp:
                            logger.info("[reg-%d] Email OTP received: %s", registration_id, otp)
                            await self._enter_otp(
                                page, otp_settings, "email_otp_field", "email_otp_submit", otp
                            )
                            result["email_otp_verified"] = True
                            result["steps_completed"].append("email_otp_verified")
                            await session.screenshot("after_email_otp")
                        else:
                            logger.warning("[reg-%d] Email OTP timed out", registration_id)
                            elapsed_ms = int((time.monotonic() - start_time) * 1000)
                            ctx = ErrorContext(
                                registration_id=registration_id,
                                category=ErrorCategory.OTP_TIMEOUT,
                                error_type="OTPTimeout",
                                error_message="Email OTP not received within timeout",
                                step_name="email_otp",
                                attempt_number=attempt_number,
                                elapsed_ms=elapsed_ms,
                            )
                            error_handler._save_debug_report(ctx)
                            result["error"] = ctx.error_message
                            result["error_context"] = ctx.to_dict()
                            await session.screenshot("email_otp_timeout")

                    # ── Step 6: Mobile OTP ──
                    if requires_mobile_otp and sms_order_id:
                        logger.info("[reg-%d] Waiting for mobile OTP...", registration_id)
                        sms_skip_count = int((custom_data or {}).get("reuse_otp_count", 0) or 0)
                        sms_known_otp = (custom_data or {}).get("reuse_last_otp") or None
                        otp = await self._get_sms_otp_with_tracking(
                            sms_provider, sms_order_id, error_handler,
                            skip_count=sms_skip_count, known_otp=sms_known_otp,
                        )
                        if otp:
                            logger.info("[reg-%d] Mobile OTP received: %s", registration_id, otp)
                            await self._enter_otp(
                                page, otp_settings, "phone_otp_field", "phone_otp_submit", otp
                            )
                            result["mobile_otp_verified"] = True
                            result["steps_completed"].append("mobile_otp_verified")
                            await session.screenshot("after_mobile_otp")
                        else:
                            logger.warning("[reg-%d] Mobile OTP timed out", registration_id)
                            elapsed_ms = int((time.monotonic() - start_time) * 1000)
                            ctx = ErrorContext(
                                registration_id=registration_id,
                                category=ErrorCategory.OTP_TIMEOUT,
                                error_type="OTPTimeout",
                                error_message="Mobile OTP not received within timeout",
                                step_name="mobile_otp",
                                attempt_number=attempt_number,
                                elapsed_ms=elapsed_ms,
                            )
                            error_handler._save_debug_report(ctx)
                            result["error"] = ctx.error_message
                            result["error_context"] = ctx.to_dict()
                            await session.screenshot("mobile_otp_timeout")

                    # ── Step 7: Success check ──
                    success = form_cfg.get("success_indicator", {})
                    if success and success.get("selector"):
                        logger.info(
                            "[reg-%d] Checking success indicator: %s",
                            registration_id, success["selector"],
                        )
                        try:
                            await page.wait_for_selector(
                                success["selector"], timeout=ELEMENT_TIMEOUT
                            )
                            result["status"] = "completed"
                            result["steps_completed"].append("success_confirmed")
                            logger.info("[reg-%d] Success indicator found!", registration_id)
                        except Exception:
                            logger.warning(
                                "[reg-%d] Success indicator not found: %s",
                                registration_id, success["selector"],
                            )
                            result["screenshot"] = await session.screenshot("no_success")
                            result["html_snapshot"] = await session.html_snapshot("no_success")
                    else:
                        if not result["error"]:
                            result["status"] = "completed"
                            result["steps_completed"].append("completed_no_indicator")
                            logger.info(
                                "[reg-%d] No success indicator configured — marking completed",
                                registration_id,
                            )

                    # Final screenshot
                    await session.screenshot("final")

                except Exception as exc:
                    elapsed_ms = int((time.monotonic() - start_time) * 1000)
                    logger.exception(
                        "[reg-%d] Registration failed at step=%s elapsed=%dms: %s",
                        registration_id,
                        result["steps_completed"][-1] if result["steps_completed"] else "unknown",
                        elapsed_ms,
                        exc,
                    )
                    ctx = await error_handler.handle_error(
                        exc,
                        session=session,
                        step="registration_flow",
                        elapsed_ms=elapsed_ms,
                        proxy_used=str(proxy.get("server", "")) if proxy else "",
                    )
                    result["error"] = ctx.error_message
                    result["error_context"] = ctx.to_dict()
                    result["screenshot"] = ctx.screenshot_path
                    result["html_snapshot"] = ctx.html_snapshot_path

                finally:
                    result["browser_log"] = session.save_logs()
                    result["browser_log_json"] = session.save_logs_json()
                    # Save Playwright trace
                    try:
                        result["trace_path"] = await session.stop_tracing()
                    except Exception:
                        pass

        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            logger.exception(
                "[reg-%d] Session-level error elapsed=%dms: %s",
                registration_id, elapsed_ms, exc,
            )
            ctx = await error_handler.handle_error(
                exc,
                step="session_acquire",
                elapsed_ms=elapsed_ms,
            )
            if not result["error"]:
                result["error"] = ctx.error_message
            result["error_context"] = ctx.to_dict()
        finally:
            reuse_rental_id = (custom_data or {}).get("reuse_rental_id") if custom_data else None
            await self._cleanup_providers(inbox_id, sms_order_id, sms_provider, result, skip_sms_release=bool(reuse_rental_id))

        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        logger.info(
            "[reg-%d] Registration finished: status=%s elapsed=%dms steps=%s error=%s",
            registration_id, result["status"], elapsed_ms,
            result["steps_completed"], result.get("error"),
        )
        return result

    # ── Cloudflare detection ───────────────────────────────

    async def _detect_cloudflare(self, page: object) -> bool:
        """Detect Cloudflare challenge / interstitial pages.

        Uses two strategies to avoid false positives:
        1. Title check — Cloudflare challenges set the title to 'Just a moment...'
        2. HTML indicator count — requires ≥2 challenge-specific patterns
        """
        try:
            title = (await page.title() or "").lower()  # type: ignore[union-attr]

            # Strategy 1: title-only check (high confidence)
            for indicator in CLOUDFLARE_TITLE_INDICATORS:
                if indicator in title:
                    logger.warning("Cloudflare title match: '%s' (title=%s)", indicator, title)
                    return True

            # Strategy 2: require ≥2 challenge-specific patterns in HTML
            html = (await page.content() or "").lower()  # type: ignore[union-attr]
            matches = [ind for ind in CLOUDFLARE_CHALLENGE_INDICATORS if ind in html]
            if len(matches) >= 2:
                logger.warning("Cloudflare challenge detected (%d matches): %s", len(matches), matches)
                return True
        except Exception:
            pass
        return False

    # ── page state checks ──────────────────────────────────

    async def _check_page_after_navigation(
        self,
        session: BrowserSession,
        error_handler: ErrorHandler,
    ) -> ErrorContext | None:
        """Check for CAPTCHA walls and proxy bans after page load."""
        try:
            html = await session.page.content()
        except Exception:
            return None

        # CAPTCHA check
        captcha_result = self._captcha_detector.detect(
            html,
            network_urls=[r["url"] for r in session.network_requests],
        )
        if captcha_result.detected:
            ctx = ErrorContext(
                registration_id=error_handler.registration_id,
                category=ErrorCategory.CAPTCHA_DETECTED,
                error_type="CaptchaDetected",
                error_message=f"CAPTCHA detected: {captcha_result.captcha_type}",
                captcha_detected=True,
                captcha_type=captcha_result.captcha_type,
                step_name="navigation",
                attempt_number=error_handler.attempt_number,
            )
            await error_handler._capture_browser_state(ctx, session)
            error_handler._save_debug_report(ctx)
            return ctx

        # Proxy ban check
        status_code = session.last_navigation_status
        ban_result = self._proxy_ban_detector.detect_from_page(html, status_code=status_code)
        if ban_result.banned or ban_result.rate_limited:
            category = (
                ErrorCategory.PROXY_BAN if ban_result.banned else ErrorCategory.PROXY_RATE_LIMITED
            )
            ctx = ErrorContext(
                registration_id=error_handler.registration_id,
                category=category,
                error_type="ProxyBanDetected" if ban_result.banned else "ProxyRateLimited",
                error_message=f"Proxy {'banned' if ban_result.banned else 'rate-limited'}: "
                f"{', '.join(ban_result.indicators)}",
                proxy_ban_indicators=ban_result.indicators,
                step_name="navigation",
                attempt_number=error_handler.attempt_number,
            )
            await error_handler._capture_browser_state(ctx, session)
            error_handler._save_debug_report(ctx)
            return ctx

        return None

    async def _validate_selectors(
        self,
        page: object,
        form_cfg: dict,
    ) -> list[str]:
        """Pre-validate configured selectors, return list of missing ones."""
        results = await self._selector_detector.check_selectors(page, form_cfg)
        return [r.selector for r in results if not r.found]

    # ── step execution ─────────────────────────────────────

    async def _execute_step(
        self,
        page: object,
        step: dict,
        step_idx: int,
        reg_data: dict,
        registration_id: int,
    ) -> None:
        """Fill fields and submit for a single form step."""
        step_url = step.get("url")
        if step_url and step_idx > 0:
            logger.info("[reg-%d] Step %d: navigating to %s", registration_id, step_idx, step_url)
            await page.goto(  # type: ignore[union-attr]
                step_url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT
            )
            await page.wait_for_timeout(1000)  # type: ignore[union-attr]

        fields = step.get("fields", {})
        if not fields:
            logger.info(
                "[reg-%d] Step %d: no fields configured, skipping to submit",
                registration_id, step_idx,
            )

        for name, cfg in fields.items():
            sel = cfg.get("selector", "")
            val = cfg.get("default_value") or reg_data.get(name, "")
            if not sel:
                logger.warning("[reg-%d] Step %d field '%s': no selector configured", registration_id, step_idx, name)
                continue
            if not val:
                logger.warning("[reg-%d] Step %d field '%s': no value available", registration_id, step_idx, name)
                continue
            try:
                logger.info(
                    "[reg-%d] Step %d: filling field '%s' (selector=%s, value=%s)",
                    registration_id, step_idx, name, sel,
                    val[:20] + "..." if len(str(val)) > 20 else val,
                )
                await page.wait_for_selector(sel, timeout=ELEMENT_TIMEOUT)  # type: ignore[union-attr]
                field_type = cfg.get("field_type", "text")
                if field_type == "checkbox":
                    await page.check(sel)  # type: ignore[union-attr]
                elif field_type == "select":
                    await page.select_option(sel, value=str(val))  # type: ignore[union-attr]
                elif field_type == "radio":
                    await page.click(sel)  # type: ignore[union-attr]
                else:
                    await page.fill(sel, str(val))  # type: ignore[union-attr]
                await page.wait_for_timeout(300)  # type: ignore[union-attr]
                logger.info("[reg-%d] Step %d: field '%s' filled OK", registration_id, step_idx, name)
            except Exception as exc:
                logger.warning(
                    "[reg-%d] Step %d field '%s' error (selector=%s): %s",
                    registration_id, step_idx, name, sel, exc,
                )

        submit = step.get("submit_button", {})
        if submit and submit.get("selector"):
            logger.info(
                "[reg-%d] Step %d: clicking submit (selector=%s)",
                registration_id, step_idx, submit["selector"],
            )
            try:
                await page.click(submit["selector"])  # type: ignore[union-attr]
                wait_ms = step.get("wait_after_submit_ms", 3000)
                await page.wait_for_timeout(wait_ms)  # type: ignore[union-attr]
                logger.info(
                    "[reg-%d] Step %d: submit clicked, waited %dms, url=%s",
                    registration_id, step_idx, wait_ms, await page.evaluate("window.location.href"),  # type: ignore[union-attr]
                )
            except Exception as exc:
                logger.error(
                    "[reg-%d] Step %d: submit click failed (selector=%s): %s",
                    registration_id, step_idx, submit["selector"], exc,
                )
                raise
        else:
            logger.info("[reg-%d] Step %d: no submit button configured", registration_id, step_idx)

    # ── OTP helpers ────────────────────────────────────────

    async def _enter_otp(
        self,
        page: object,
        otp_settings: dict,
        field_key: str,
        submit_key: str,
        otp: str,
    ) -> None:
        """Enter OTP using the nested otp_settings structure."""
        field = otp_settings.get(field_key, {})
        if not (field and field.get("selector")):
            return

        otp_page_url = otp_settings.get("otp_page_url")
        if otp_page_url:
            await page.goto(  # type: ignore[union-attr]
                otp_page_url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT
            )
            await page.wait_for_timeout(1000)  # type: ignore[union-attr]

        if field and field.get("selector"):
            await page.wait_for_selector(  # type: ignore[union-attr]
                field["selector"], timeout=OTP_ELEMENT_TIMEOUT
            )
            await page.fill(field["selector"], otp)  # type: ignore[union-attr]
            submit = otp_settings.get(submit_key, {})
            if submit and submit.get("selector"):
                await page.click(submit["selector"])  # type: ignore[union-attr]
                await page.wait_for_timeout(3000)  # type: ignore[union-attr]

    async def _get_email_otp_with_tracking(
        self,
        inbox_id: str,
        error_handler: ErrorHandler,
    ) -> str | None:
        """Poll for email OTP with timeout tracking."""
        tracker = OTPTimeoutDetector(max_wait_seconds=120.0)
        tracker.start_polling()
        otp = await self.mailslurp.get_otp(inbox_id=inbox_id)
        if not otp:
            timeout_result = tracker.build_timeout_result(
                otp_type="email",
                provider="mailslurp",
                inbox_id=inbox_id,
            )
            logger.warning(
                "Email OTP timeout: waited %.1fs, %d polls",
                timeout_result.wait_seconds,
                timeout_result.poll_attempts,
            )
        return otp

    async def _get_sms_otp_with_tracking(
        self,
        provider: str | None,
        order_id: str,
        error_handler: ErrorHandler,
        skip_count: int = 0,
        known_otp: str | None = None,
    ) -> str | None:
        """Poll for SMS OTP with timeout tracking."""
        tracker = OTPTimeoutDetector(max_wait_seconds=120.0)
        tracker.start_polling()
        otp = await self._get_sms_otp(provider, order_id, skip_count=skip_count, known_otp=known_otp)
        if not otp:
            timeout_result = tracker.build_timeout_result(
                otp_type="mobile",
                provider=provider or "unknown",
            )
            logger.warning(
                "Mobile OTP timeout: waited %.1fs, %d polls",
                timeout_result.wait_seconds,
                timeout_result.poll_attempts,
            )
        return otp

    async def _get_sms_otp(
        self, provider: str | None, order_id: str,
        skip_count: int = 0, known_otp: str | None = None,
    ) -> str | None:
        if provider == "5sim":
            return await self.fivesim.get_otp(order_id=order_id, skip_count=skip_count)
        if provider == "pvapins":
            return await self.pvapins.get_otp(order_id=order_id, known_otp=known_otp)
        return None

    # ── cleanup ────────────────────────────────────────────

    async def _cleanup_providers(
        self,
        inbox_id: str | None,
        sms_order_id: str | None,
        sms_provider: str | None,
        result: dict,
        skip_sms_release: bool = False,
    ) -> None:
        """Release provisioned email inboxes and phone numbers."""
        if inbox_id:
            try:
                await self.mailslurp.delete_inbox(inbox_id)
            except Exception:
                logger.debug("Failed to delete inbox %s", inbox_id)
        if sms_order_id and not skip_sms_release:
            try:
                if sms_provider == "5sim":
                    if result.get("mobile_otp_verified"):
                        await self.fivesim.finish_order(sms_order_id)
                    else:
                        await self.fivesim.cancel_order(sms_order_id)
                elif sms_provider == "pvapins":
                    await self.pvapins.release_number(sms_order_id)
            except Exception:
                logger.debug("Failed to cleanup SMS order %s", sms_order_id)
