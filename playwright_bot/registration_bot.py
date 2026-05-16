import logging
import os
from datetime import datetime, timezone

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from configs.settings import settings
from otp.fivesim_service import FiveSimService
from otp.mailslurp_service import MailSlurpService
from otp.pvapins_service import PVAPinsService
from utils.data_generator import generate_registration_data

logger = logging.getLogger(__name__)

SCREENSHOT_DIR = "screenshots"


class RegistrationBot:
    """Headless Playwright bot that automates website registration.

    Supports the nested ``FormConfig`` schema produced by the API:
        form_config.steps[]        — multi-step form filling
        form_config.otp_settings   — OTP field selectors
        form_config.captcha_settings (not yet automated)
        form_config.success_indicator
    """

    def __init__(self) -> None:
        self.mailslurp = MailSlurpService()
        self.fivesim = FiveSimService()
        self.pvapins = PVAPinsService()
        self._pw = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    # ── lifecycle ──────────────────────────────────────────────

    async def start_browser(self) -> None:
        self._pw = await async_playwright().start()
        proxy = {"server": settings.PROXY_URL} if settings.PROXY_URL else None
        self.browser = await self._pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            proxy=proxy,
        )
        await self.context.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
        )
        self.page = await self.context.new_page()
        logger.info("Browser started")

    async def close_browser(self) -> None:
        for resource in (self.page, self.context, self.browser):
            if resource:
                await resource.close()
        if self._pw:
            await self._pw.stop()
        logger.info("Browser closed")

    # ── main flow ──────────────────────────────────────────────

    async def register(
        self,
        website_config: dict,
        registration_id: int,
        requires_email_otp: bool = False,
        requires_mobile_otp: bool = False,
        custom_data: dict | None = None,
    ) -> dict:
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
        }
        inbox_id: str | None = None
        sms_order_id: str | None = None
        sms_provider: str | None = None

        try:
            await self.start_browser()
            assert self.page is not None

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
                sms_order_id = num["order_id"]
                reg_data["phone"] = num["phone_number"]
                result["phone_used"] = reg_data["phone"]

            # 3) navigate to registration page
            form_cfg = website_config.get("form_config", {})
            url = form_cfg.get("registration_url", website_config.get("url", ""))
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            await self.page.wait_for_timeout(2000)

            # 4) fill fields + submit — iterate over steps for multi-step support
            steps = form_cfg.get("steps", [])
            for step_idx, step in enumerate(steps):
                step_url = step.get("url")
                if step_url and step_idx > 0:
                    await self.page.goto(step_url, wait_until="domcontentloaded", timeout=30_000)
                    await self.page.wait_for_timeout(1000)

                for name, cfg in step.get("fields", {}).items():
                    sel = cfg.get("selector", "")
                    val = cfg.get("default_value") or reg_data.get(name, "")
                    if not sel or not val:
                        continue
                    try:
                        await self.page.wait_for_selector(sel, timeout=10_000)
                        await self.page.fill(sel, str(val))
                        await self.page.wait_for_timeout(300)
                    except Exception as exc:
                        logger.warning("Step %d field '%s' fill error: %s", step_idx, name, exc)

                submit = step.get("submit_button", {})
                if submit and submit.get("selector"):
                    await self.page.click(submit["selector"])
                    wait_ms = step.get("wait_after_submit_ms", 3000)
                    await self.page.wait_for_timeout(wait_ms)

            # 5) email OTP
            otp_settings = form_cfg.get("otp_settings") or {}
            if requires_email_otp and inbox_id:
                otp = await self.mailslurp.get_otp(inbox_id=inbox_id)
                if otp:
                    await self._enter_otp_nested(
                        otp_settings,
                        field_key="email_otp_field",
                        submit_key="email_otp_submit",
                        otp=otp,
                    )
                    result["email_otp_verified"] = True
                else:
                    result["error"] = "Email OTP not received"

            # 6) mobile OTP
            if requires_mobile_otp and sms_order_id:
                otp = None
                if sms_provider == "5sim":
                    otp = await self.fivesim.get_otp(order_id=sms_order_id)
                elif sms_provider == "pvapins":
                    otp = await self.pvapins.get_otp(order_id=sms_order_id)
                if otp:
                    await self._enter_otp_nested(
                        otp_settings,
                        field_key="phone_otp_field",
                        submit_key="phone_otp_submit",
                        otp=otp,
                    )
                    result["mobile_otp_verified"] = True
                else:
                    result["error"] = "Mobile OTP not received"

            # 7) success check
            success = form_cfg.get("success_indicator", {})
            if success and success.get("selector"):
                try:
                    await self.page.wait_for_selector(success["selector"], timeout=10_000)
                    result["status"] = "completed"
                except Exception:
                    result["screenshot"] = await self._screenshot(registration_id)
            else:
                if not result["error"]:
                    result["status"] = "completed"

        except Exception as exc:
            result["error"] = str(exc)
            logger.exception("Registration %d failed", registration_id)
            try:
                result["screenshot"] = await self._screenshot(registration_id)
            except Exception:
                pass
        finally:
            await self._cleanup(inbox_id, sms_order_id, sms_provider, result)
            await self.close_browser()

        return result

    # ── helpers ────────────────────────────────────────────────

    async def _enter_otp_nested(
        self, otp_settings: dict, field_key: str, submit_key: str, otp: str
    ) -> None:
        """Enter OTP using the nested otp_settings structure."""
        assert self.page is not None
        field = otp_settings.get(field_key, {})
        if field and field.get("selector"):
            otp_page_url = otp_settings.get("otp_page_url")
            if otp_page_url:
                await self.page.goto(otp_page_url, wait_until="domcontentloaded", timeout=30_000)
                await self.page.wait_for_timeout(1000)
            await self.page.wait_for_selector(field["selector"], timeout=15_000)
            await self.page.fill(field["selector"], otp)
            submit = otp_settings.get(submit_key, {})
            if submit and submit.get("selector"):
                await self.page.click(submit["selector"])
                await self.page.wait_for_timeout(3000)

    async def _screenshot(self, reg_id: int) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = f"{SCREENSHOT_DIR}/reg_{reg_id}_{ts}.png"
        if self.page:
            await self.page.screenshot(path=path, full_page=True)
        return path

    async def _cleanup(
        self,
        inbox_id: str | None,
        sms_order_id: str | None,
        sms_provider: str | None,
        result: dict,
    ) -> None:
        if inbox_id:
            await self.mailslurp.delete_inbox(inbox_id)
        if sms_order_id:
            if sms_provider == "5sim":
                if result.get("mobile_otp_verified"):
                    await self.fivesim.finish_order(sms_order_id)
                else:
                    await self.fivesim.cancel_order(sms_order_id)
            elif sms_provider == "pvapins":
                await self.pvapins.release_number(sms_order_id)
