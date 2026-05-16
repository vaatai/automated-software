"""Registration bot — drives multi-step form filling using BrowserManager sessions."""

import logging

from otp.fivesim_service import FiveSimService
from otp.mailslurp_service import MailSlurpService
from otp.pvapins_service import PVAPinsService
from playwright_bot.browser_manager import BrowserManager
from utils.data_generator import generate_registration_data

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
    """

    def __init__(self, browser_manager: BrowserManager) -> None:
        self.manager = browser_manager
        self.mailslurp = MailSlurpService()
        self.fivesim = FiveSimService()
        self.pvapins = PVAPinsService()

    async def register(
        self,
        website_config: dict,
        registration_id: int,
        requires_email_otp: bool = False,
        requires_mobile_otp: bool = False,
        custom_data: dict | None = None,
        proxy: dict | None = None,
    ) -> dict:
        """Execute a full registration flow inside an isolated browser session."""
        result: dict = {
            "registration_id": registration_id,
            "status": "failed",
            "email_used": None,
            "phone_used": None,
            "username": None,
            "email_otp_verified": False,
            "mobile_otp_verified": False,
            "error": None,
            "screenshot": None,
            "browser_log": None,
        }
        inbox_id: str | None = None
        sms_order_id: str | None = None
        sms_provider: str | None = None

        session_id = f"reg-{registration_id}"

        try:
            async with self.manager.acquire_session(
                session_id=session_id, proxy=proxy
            ) as session:
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

                    # 2) provision phone number (5SIM → PVAPins fallback)
                    if requires_mobile_otp:
                        try:
                            num = await self.fivesim.rent_number()
                            sms_provider = "5sim"
                        except Exception:
                            num = await self.pvapins.rent_number()
                            sms_provider = "pvapins"
                        sms_order_id = num.order_id
                        reg_data["phone"] = num.phone_number
                        result["phone_used"] = reg_data["phone"]

                    # 3) navigate to registration page
                    form_cfg = website_config.get("form_config", {})
                    url = form_cfg.get(
                        "registration_url", website_config.get("url", "")
                    )
                    await page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=NAVIGATION_TIMEOUT,
                    )
                    await page.wait_for_timeout(2000)

                    # 4) fill fields + submit — iterate over steps
                    steps = form_cfg.get("steps", [])
                    for step_idx, step in enumerate(steps):
                        await self._execute_step(
                            page, step, step_idx, reg_data
                        )

                    # 5) email OTP
                    otp_settings = form_cfg.get("otp_settings") or {}
                    if requires_email_otp and inbox_id:
                        otp = await self.mailslurp.get_otp(inbox_id=inbox_id)
                        if otp:
                            await self._enter_otp(
                                page, otp_settings, "email_otp_field", "email_otp_submit", otp
                            )
                            result["email_otp_verified"] = True
                        else:
                            result["error"] = "Email OTP not received"

                    # 6) mobile OTP
                    if requires_mobile_otp and sms_order_id:
                        otp = await self._get_sms_otp(sms_provider, sms_order_id)
                        if otp:
                            await self._enter_otp(
                                page, otp_settings, "phone_otp_field", "phone_otp_submit", otp
                            )
                            result["mobile_otp_verified"] = True
                        else:
                            result["error"] = "Mobile OTP not received"

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
                    else:
                        if not result["error"]:
                            result["status"] = "completed"

                except Exception as exc:
                    result["error"] = str(exc)
                    logger.exception("Registration %d failed", registration_id)
                    try:
                        result["screenshot"] = await session.screenshot("exception")
                    except Exception:
                        pass
                finally:
                    result["browser_log"] = session.save_logs()

        except Exception as exc:
            if not result["error"]:
                result["error"] = str(exc)
            logger.exception("Registration %d session error", registration_id)
        finally:
            await self._cleanup_providers(inbox_id, sms_order_id, sms_provider, result)

        return result

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
    ) -> None:
        """Release provisioned email inboxes and phone numbers."""
        if inbox_id:
            try:
                await self.mailslurp.delete_inbox(inbox_id)
            except Exception:
                logger.debug("Failed to delete inbox %s", inbox_id)
        if sms_order_id:
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
