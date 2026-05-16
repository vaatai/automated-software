import logging
import time

import httpx

from configs.settings import settings
from otp.base import BaseOTPService

logger = logging.getLogger(__name__)


class PVAPinsService(BaseOTPService):
    """Backup SMS OTP provider via PVAPins."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.PVAPINS_API_KEY
        self.base_url = settings.PVAPINS_BASE_URL

    async def rent_number(self, service: str = "opt4", country: str = "US") -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/getNumber",
                params={"apikey": self.api_key, "service": service, "country": country},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("error"):
                raise RuntimeError(f"PVAPins error: {data['error']}")
            logger.info("Rented PVAPins number: %s (order %s)", data.get("number"), data.get("id"))
            return {"order_id": str(data["id"]), "phone_number": data["number"]}

    async def get_otp(self, *, order_id: str, **kwargs: object) -> str | None:
        timeout = int(kwargs.get("timeout", settings.OTP_POLL_TIMEOUT_SECONDS) or 0)
        interval = int(kwargs.get("interval", settings.OTP_POLL_INTERVAL_SECONDS) or 0)
        start = time.time()

        async with httpx.AsyncClient() as client:
            while time.time() - start < timeout:
                try:
                    resp = await client.get(
                        f"{self.base_url}/getSMS",
                        params={"apikey": self.api_key, "id": order_id},
                        timeout=15,
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    sms_code = data.get("sms")
                    if sms_code and sms_code != "wait":
                        otp = self.extract_otp(str(sms_code))
                        if otp:
                            logger.info("PVAPins OTP: %s", otp)
                            return otp

                    if data.get("error"):
                        logger.warning("PVAPins error: %s", data["error"])
                        return None
                except httpx.HTTPStatusError as exc:
                    logger.warning("PVAPins HTTP error: %s", exc.response.status_code)

                await self.async_sleep(interval)

        logger.error("PVAPins OTP timed out after %ds", timeout)
        return None

    async def release_number(self, order_id: str) -> None:
        async with httpx.AsyncClient() as client:
            try:
                await client.get(
                    f"{self.base_url}/setStatus",
                    params={"apikey": self.api_key, "id": order_id, "status": "cancel"},
                    timeout=15,
                )
            except Exception as exc:
                logger.warning("release_number failed: %s", exc)
