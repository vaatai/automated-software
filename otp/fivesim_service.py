import logging
import time

import httpx

from configs.settings import settings
from otp.base import BaseOTPService

logger = logging.getLogger(__name__)


class FiveSimService(BaseOTPService):
    """Primary SMS OTP provider via 5SIM."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.FIVESIM_API_KEY
        self.base_url = settings.FIVESIM_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

    async def rent_number(
        self, country: str = "any", service: str = "any", operator: str = "any"
    ) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/user/buy/activation/{country}/{operator}/{service}",
                headers=self.headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info("Rented 5SIM number: %s (order %s)", data.get("phone"), data.get("id"))
            return {
                "order_id": str(data["id"]),
                "phone_number": data["phone"],
            }

    async def get_otp(self, *, order_id: str, **kwargs: object) -> str | None:
        timeout = int(kwargs.get("timeout", settings.OTP_POLL_TIMEOUT_SECONDS) or 0)
        interval = int(kwargs.get("interval", settings.OTP_POLL_INTERVAL_SECONDS) or 0)
        start = time.time()

        async with httpx.AsyncClient() as client:
            while time.time() - start < timeout:
                try:
                    resp = await client.get(
                        f"{self.base_url}/user/check/{order_id}",
                        headers=self.headers,
                        timeout=15,
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    sms_list = data.get("sms", [])
                    if sms_list:
                        code = sms_list[0].get("code", "")
                        otp = code or self.extract_otp(sms_list[0].get("text", ""))
                        if otp:
                            logger.info("5SIM OTP: %s", otp)
                            return otp

                    if data.get("status") in ("TIMEOUT", "CANCELED"):
                        return None
                except httpx.HTTPStatusError as exc:
                    logger.warning("5SIM error: %s", exc.response.status_code)

                await self.async_sleep(interval)

        logger.error("5SIM OTP timed out after %ds", timeout)
        return None

    async def finish_order(self, order_id: str) -> None:
        async with httpx.AsyncClient() as client:
            try:
                await client.get(
                    f"{self.base_url}/user/finish/{order_id}",
                    headers=self.headers,
                    timeout=15,
                )
            except Exception as exc:
                logger.warning("finish_order failed: %s", exc)

    async def cancel_order(self, order_id: str) -> None:
        async with httpx.AsyncClient() as client:
            try:
                await client.get(
                    f"{self.base_url}/user/cancel/{order_id}",
                    headers=self.headers,
                    timeout=15,
                )
            except Exception as exc:
                logger.warning("cancel_order failed: %s", exc)
