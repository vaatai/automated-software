"""PVAPins SMS OTP provider adapter.

Secondary SMS provider. Provides number rental and SMS polling
with country/service selection.

API docs: https://pvapins.com/api-documentation
"""

import logging
import time

import httpx

from configs.settings import settings
from otp.base import BaseOTPService
from otp.sms_provider import (
    NumberUnavailableError,
    ProviderError,
    ProviderStatus,
    RentalResult,
    SMSProviderAdapter,
    SMSResult,
)

logger = logging.getLogger(__name__)


class PVAPinsService(BaseOTPService, SMSProviderAdapter):
    """Secondary SMS OTP provider via PVAPins.

    Implements both the legacy BaseOTPService interface (for backward compat)
    and the new SMSProviderAdapter interface (for OTPManager).
    """

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or settings.PVAPINS_API_KEY
        self._base_url = settings.PVAPINS_BASE_URL

    @property
    def provider_name(self) -> str:
        return "pvapins"

    @property
    def priority(self) -> int:
        return 2

    # ── SMSProviderAdapter interface ───────────────────────

    async def rent_number(
        self,
        country: str = "US",
        service: str = "opt4",
        operator: str = "any",
    ) -> RentalResult:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{self._base_url}/getNumber",
                    params={
                        "apikey": self._api_key,
                        "service": service,
                        "country": country,
                    },
                    timeout=30,
                )
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise ProviderError(
                    self.provider_name,
                    f"HTTP {exc.response.status_code}",
                    exc.response.status_code,
                )

            data = resp.json()

            if data.get("error"):
                error_msg = data["error"]
                if "no numbers" in error_msg.lower() or "not available" in error_msg.lower():
                    raise NumberUnavailableError(self.provider_name, country, service)
                raise ProviderError(self.provider_name, error_msg)

            logger.info(
                "PVAPins rented number: %s (order %s)",
                data.get("number"),
                data.get("id"),
            )
            return RentalResult(
                order_id=str(data["id"]),
                phone_number=data["number"],
                provider=self.provider_name,
                country=country,
                service=service,
            )

    async def poll_for_otp(
        self,
        order_id: str,
        timeout: int = 120,
        interval: int = 5,
    ) -> SMSResult:
        start = time.monotonic()

        async with httpx.AsyncClient() as client:
            while time.monotonic() - start < timeout:
                try:
                    resp = await client.get(
                        f"{self._base_url}/getSMS",
                        params={"apikey": self._api_key, "id": order_id},
                        timeout=15,
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    sms_code = data.get("sms")
                    if sms_code and sms_code != "wait":
                        raw_text = str(sms_code)
                        otp = self.extract_otp(raw_text)
                        if otp:
                            logger.info("PVAPins OTP extracted: %s", otp)
                            return SMSResult(
                                otp=otp,
                                raw_message=raw_text,
                                provider=self.provider_name,
                                order_id=order_id,
                            )

                    if data.get("error"):
                        logger.warning("PVAPins error: %s", data["error"])
                        return SMSResult(otp=None, provider=self.provider_name, order_id=order_id)

                except httpx.HTTPStatusError as exc:
                    logger.warning("PVAPins poll error: %s", exc.response.status_code)

                await self.async_sleep(interval)

        logger.error("PVAPins OTP timed out after %ds", timeout)
        return SMSResult(otp=None, provider=self.provider_name, order_id=order_id)

    async def release_number(self, order_id: str, success: bool = False) -> None:
        status = "complete" if success else "cancel"
        async with httpx.AsyncClient() as client:
            try:
                await client.get(
                    f"{self._base_url}/setStatus",
                    params={"apikey": self._api_key, "id": order_id, "status": status},
                    timeout=15,
                )
                logger.info("PVAPins order %s: %s", order_id, status)
            except Exception as exc:
                logger.warning("PVAPins release_number failed: %s", exc)

    async def check_balance(self) -> float | None:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{self._base_url}/getBalance",
                    params={"apikey": self._api_key},
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()
                return float(data.get("balance", 0))
            except Exception:
                return None

    async def get_status(self) -> ProviderStatus:
        balance = await self.check_balance()
        if balance is None:
            return ProviderStatus.ERROR
        if balance <= 0:
            return ProviderStatus.DISABLED
        return ProviderStatus.AVAILABLE

    # ── Legacy BaseOTPService interface ────────────────────

    async def get_otp(self, *, order_id: str, **kwargs: object) -> str | None:
        timeout = int(kwargs.get("timeout", settings.OTP_POLL_TIMEOUT_SECONDS) or 0)
        interval = int(kwargs.get("interval", settings.OTP_POLL_INTERVAL_SECONDS) or 0)
        result = await self.poll_for_otp(order_id, timeout=timeout, interval=interval)
        return result.otp
