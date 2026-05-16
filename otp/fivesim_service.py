"""5SIM SMS OTP provider adapter.

Primary SMS provider. Supports country/service/operator selection,
rental lifecycle management, and balance checking.

API docs: https://docs.5sim.net/
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


class FiveSimService(BaseOTPService, SMSProviderAdapter):
    """Primary SMS OTP provider via 5SIM.

    Implements both the legacy BaseOTPService interface (for backward compat)
    and the new SMSProviderAdapter interface (for OTPManager).
    """

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or settings.FIVESIM_API_KEY
        self._base_url = settings.FIVESIM_BASE_URL
        self._headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
        }

    @property
    def provider_name(self) -> str:
        return "5sim"

    @property
    def priority(self) -> int:
        return 1

    # ── SMSProviderAdapter interface ───────────────────────

    async def rent_number(
        self,
        country: str = "any",
        service: str = "any",
        operator: str = "any",
    ) -> RentalResult:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{self._base_url}/user/buy/activation/{country}/{operator}/{service}",
                    headers=self._headers,
                    timeout=30,
                )
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    raise NumberUnavailableError(self.provider_name, country, service)
                raise ProviderError(
                    self.provider_name,
                    f"HTTP {exc.response.status_code}",
                    exc.response.status_code,
                )

            data = resp.json()

            if data.get("status") == "no free phones":
                raise NumberUnavailableError(self.provider_name, country, service)

            logger.info(
                "5SIM rented number: %s (order %s)", data.get("phone"), data.get("id")
            )
            return RentalResult(
                order_id=str(data["id"]),
                phone_number=data["phone"],
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
                        f"{self._base_url}/user/check/{order_id}",
                        headers=self._headers,
                        timeout=15,
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    sms_list = data.get("sms", [])
                    if sms_list:
                        raw_text = sms_list[0].get("text", "")
                        code = sms_list[0].get("code", "")
                        otp = code or self.extract_otp(raw_text)
                        if otp:
                            logger.info("5SIM OTP extracted: %s", otp)
                            return SMSResult(
                                otp=otp,
                                raw_message=raw_text,
                                provider=self.provider_name,
                                order_id=order_id,
                            )

                    if data.get("status") in ("TIMEOUT", "CANCELED"):
                        return SMSResult(otp=None, provider=self.provider_name, order_id=order_id)

                except httpx.HTTPStatusError as exc:
                    logger.warning("5SIM poll error: %s", exc.response.status_code)

                await self.async_sleep(interval)

        logger.error("5SIM OTP timed out after %ds", timeout)
        return SMSResult(otp=None, provider=self.provider_name, order_id=order_id)

    async def release_number(self, order_id: str, success: bool = False) -> None:
        endpoint = "finish" if success else "cancel"
        async with httpx.AsyncClient() as client:
            try:
                await client.get(
                    f"{self._base_url}/user/{endpoint}/{order_id}",
                    headers=self._headers,
                    timeout=15,
                )
                logger.info("5SIM order %s: %s", order_id, endpoint)
            except Exception as exc:
                logger.warning("5SIM release_number failed: %s", exc)

    async def check_balance(self) -> float | None:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{self._base_url}/user/profile",
                    headers=self._headers,
                    timeout=15,
                )
                resp.raise_for_status()
                return float(resp.json().get("balance", 0))
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

    async def finish_order(self, order_id: str) -> None:
        await self.release_number(order_id, success=True)

    async def cancel_order(self, order_id: str) -> None:
        await self.release_number(order_id, success=False)
