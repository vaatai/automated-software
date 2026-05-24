"""Registration bot — drives multi-step form filling using BrowserManager sessions.

Integrates centralized error handling for:
  - Screenshot + HTML snapshot capture on every failure
  - Browser console + network request logging
  - CAPTCHA detection, selector change detection
  - OTP timeout tracking
  - Proxy ban detection
  - Rich ErrorContext for post-mortem debugging
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
        }
        inbox_id: str | None = None
        sms_order_id: str | None = None
        sms_provider: str | None = None

        session_id = f"reg-{registration_id}"

        try:
            async with self.manager.acquire_session(session_id=session_id, proxy=proxy) as session:
                try:
                    page = session.page

                    reg_data = generate_registration_data()
                    if custom_data:
                        reg_data.update(custom_data)
                    result["username"] = reg_data.get("username")

                    # 1) provision temp email
                    if requires_email_otp:
                        inbox = await self.mailslurp.create_inbox()
                        inbox_id = inbox["inbox_id"]
                        reg_data["email"] = inbox["email_address"]
                        result["email_used"] = reg_data["email"]

                    # 2) provision phone number (reuse active rental or rent new)
                    if requires_mobile_otp:
                        phone_country = (custom_data or {}).get("phone_country", "US")
                        reuse_rental_id = (custom_data or {}).get("reuse_rental_id")

                        if reuse_rental_id:
                            # Reuse an existing rented number
                            from otp.sms_provider import RentalResult
                            reuse_phone = (custom_data or {}).get("reuse_phone", "")
                            reuse_provider = (custom_data or {}).get("reuse_provider", "5sim")
                            reuse_order_id = (custom_data or {}).get("reuse_order_id", "")
                            sms_provider = reuse_provider
                            sms_order_id = reuse_order_id
                            reg_data["phone"] = reuse_phone
                            result["phone_used"] = reuse_phone
                            logger.info(
                                "Reusing rental #%s phone=%s for registration %d",
                                reuse_rental_id, reuse_phone, registration_id,
                            )
                        else:
                            try:
                                num = await self.fivesim.rent_number(country=phone_country)
                                sms_provider = "5sim"
                            except Exception:
                                num = await self.pvapins.rent_number(country=phone_country)
                                sms_provider = "pvapins"
                            sms_order_id = num.order_id
                            reg_data["phone"] = num.phone_number
                            result["phone_used"] = reg_data["phone"]

                    # 3) navigate to registration page
                    form_cfg = website_config.get("form_config", {})
                    url = form_cfg.get("registration_url", website_config.get("url", ""))
                    await page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=NAVIGATION_TIMEOUT,
                    )
                    await page.wait_for_timeout(2000)

                    # 3a) check for CAPTCHA / proxy ban after navigation
                    page_check = await self._check_page_after_navigation(session, error_handler)
                    if page_check is not None:
                        result["error"] = page_check.error_message
                        result["error_context"] = page_check.to_dict()
                        result["screenshot"] = page_check.screenshot_path
                        result["html_snapshot"] = page_check.html_snapshot_path
                        return result

                    # 3b) validate selectors before filling
                    selector_failures = await self._validate_selectors(page, form_cfg)
                    if selector_failures:
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

                    # 4) fill fields + submit — iterate over steps
                    steps = form_cfg.get("steps", [])
                    for step_idx, step in enumerate(steps):
                        await self._execute_step(page, step, step_idx, reg_data)
                        # Check page state after each step
                        step_check = await error_handler.check_page_state(
                            session, step=f"step_{step_idx}_submit"
                        )
                        if step_check is not None:
                            result["error"] = step_check.error_message
                            result["error_context"] = step_check.to_dict()
                            result["screenshot"] = step_check.screenshot_path
                            return result

                    # 5) email OTP
                    otp_settings = form_cfg.get("otp_settings") or {}
                    if requires_email_otp and inbox_id:
                        otp = await self._get_email_otp_with_tracking(inbox_id, error_handler)
                        if otp:
                            await self._enter_otp(
                                page, otp_settings, "email_otp_field", "email_otp_submit", otp
                            )
                            result["email_otp_verified"] = True
                        else:
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

                    # 6) mobile OTP
                    if requires_mobile_otp and sms_order_id:
                        otp = await self._get_sms_otp_with_tracking(
                            sms_provider, sms_order_id, error_handler
                        )
                        if otp:
                            await self._enter_otp(
                                page, otp_settings, "phone_otp_field", "phone_otp_submit", otp
                            )
                            result["mobile_otp_verified"] = True
                        else:
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

                    # 7) success check
                    success = form_cfg.get("success_indicator", {})
                    if success and success.get("selector"):
                        try:
                            await page.wait_for_selector(
                                success["selector"], timeout=ELEMENT_TIMEOUT
                            )
                            result["status"] = "completed"
                        except Exception:
                            result["screenshot"] = await session.screenshot("no_success")
                            result["html_snapshot"] = await session.html_snapshot("no_success")
                    else:
                        if not result["error"]:
                            result["status"] = "completed"

                except Exception as exc:
                    elapsed_ms = int((time.monotonic() - start_time) * 1000)
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
                    logger.exception("Registration %d failed", registration_id)

                finally:
                    result["browser_log"] = session.save_logs()
                    result["browser_log_json"] = session.save_logs_json()

        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            ctx = await error_handler.handle_error(
                exc,
                step="session_acquire",
                elapsed_ms=elapsed_ms,
            )
            if not result["error"]:
                result["error"] = ctx.error_message
            result["error_context"] = ctx.to_dict()
            logger.exception("Registration %d session error", registration_id)
        finally:
            reuse_rental_id = (custom_data or {}).get("reuse_rental_id") if custom_data else None
            await self._cleanup_providers(inbox_id, sms_order_id, sms_provider, result, skip_sms_release=bool(reuse_rental_id))

        return result

    # ── page state checks ──────────────────────────────────

    async def _check_page_after_navigation(
        self,
        session: BrowserSession,
        error_handler: ErrorHandler,
    ) -> ErrorContext | None:
        """Check for CAPTCHA walls and proxy bans after page load.

        Constructs ErrorContext directly from detector results rather than
        delegating to check_page_state, so HTTP-status-only detections
        (e.g. 403 with generic HTML) are never silently dropped.
        """
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
    ) -> None:
        """Fill fields and submit for a single form step."""
        step_url = step.get("url")
        if step_url and step_idx > 0:
            await page.goto(  # type: ignore[union-attr]
                step_url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT
            )
            await page.wait_for_timeout(1000)  # type: ignore[union-attr]

        for name, cfg in step.get("fields", {}).items():
            sel = cfg.get("selector", "")
            val = cfg.get("default_value") or reg_data.get(name, "")
            if not sel or not val:
                continue
            try:
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
            except Exception as exc:
                logger.warning("Step %d field '%s' error: %s", step_idx, name, exc)

        submit = step.get("submit_button", {})
        if submit and submit.get("selector"):
            await page.click(submit["selector"])  # type: ignore[union-attr]
            wait_ms = step.get("wait_after_submit_ms", 3000)
            await page.wait_for_timeout(wait_ms)  # type: ignore[union-attr]

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
    ) -> str | None:
        """Poll for SMS OTP with timeout tracking."""
        tracker = OTPTimeoutDetector(max_wait_seconds=120.0)
        tracker.start_polling()
        otp = await self._get_sms_otp(provider, order_id)
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

    async def _get_sms_otp(self, provider: str | None, order_id: str) -> str | None:
        if provider == "5sim":
            return await self.fivesim.get_otp(order_id=order_id)
        if provider == "pvapins":
            return await self.pvapins.get_otp(order_id=order_id)
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
