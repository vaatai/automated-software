"""SMS-Activate provider adapter.

Backup SMS provider. Large inventory of numbers across many countries.

API docs: https://sms-activate.org/en/api2
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

# ISO 2-letter code -> SMS-Activate numeric country ID
# Full list: https://sms-activate.org/en/api2#getCountries
ISO_TO_SMSACTIVATE: dict[str, str] = {
    "RU": "0", "UA": "1", "KZ": "2", "CN": "3", "PH": "4",
    "ID": "6", "MY": "7", "KE": "8", "TZ": "9", "NG": "19",
    "EG": "21", "IN": "22", "IE": "23", "GB": "16", "US": "12",
    "IL": "13", "PL": "15", "SE": "46", "NL": "48", "CA": "36",
    "DE": "43", "FR": "78", "ES": "56", "IT": "86", "BR": "73",
    "AU": "175", "JP": "182", "KR": "190", "TR": "62", "TH": "52",
    "VN": "10", "ZA": "31", "CO": "33", "MX": "54", "PK": "14",
}


class SMSActivateService(BaseOTPService, SMSProviderAdapter):
    """Backup SMS OTP provider via SMS-Activate.

    Implements both the legacy BaseOTPService interface (for backward compat)
    and the new SMSProviderAdapter interface (for OTPManager).
    """

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or settings.SMSACTIVATE_API_KEY
        self._base_url = settings.SMSACTIVATE_BASE_URL

    @property
    def provider_name(self) -> str:
        return "sms-activate"

    @property
    def priority(self) -> int:
        return 3

    # ── SMSProviderAdapter interface ───────────────────────

    async def rent_number(
        self,
        country: str = "0",
        service: str = "go",
        operator: str = "any",
    ) -> RentalResult:
        """Rent a number via SMS-Activate.

        Args:
            country: Country ID (SMS-Activate uses numeric IDs, "0" = Russia default).
            service: Service short code (e.g., "go" for Google, "tg" for Telegram).
            operator: Operator preference (not widely used, passed as-is).
        """
        api_country = ISO_TO_SMSACTIVATE.get(country.upper(), country) if country != "any" else "0"
        params = {
            "api_key": self._api_key,
            "action": "getNumber",
            "service": service,
            "country": api_country,
        }
        if operator != "any":
            params["operator"] = operator

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    self._base_url,
                    params=params,
                    timeout=30,
                )
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise ProviderError(
                    self.provider_name,
                    f"HTTP {exc.response.status_code}",
                    exc.response.status_code,
                )

            text = resp.text.strip()

            if text == "NO_NUMBERS":
                raise NumberUnavailableError(self.provider_name, country, service)
            if text == "NO_BALANCE":
                raise ProviderError(self.provider_name, "Insufficient balance")
            if not text.startswith("ACCESS_NUMBER"):
                raise ProviderError(self.provider_name, f"Unexpected response: {text}")

            # Format: ACCESS_NUMBER:ORDER_ID:PHONE_NUMBER
            parts = text.split(":")
            order_id = parts[1]
            phone_number = parts[2]

            logger.info(
                "SMS-Activate rented number: %s (order %s)", phone_number, order_id
            )
            return RentalResult(
                order_id=order_id,
                phone_number=phone_number,
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
                        self._base_url,
                        params={
                            "api_key": self._api_key,
                            "action": "getStatus",
                            "id": order_id,
                        },
                        timeout=15,
                    )
                    resp.raise_for_status()
                    text = resp.text.strip()

                    # STATUS_OK:CODE — SMS received
                    if text.startswith("STATUS_OK:"):
                        code = text.split(":", 1)[1]
                        otp = self.extract_otp(code) or code
                        logger.info("SMS-Activate OTP extracted: %s", otp)
                        return SMSResult(
                            otp=otp,
                            raw_message=code,
                            provider=self.provider_name,
                            order_id=order_id,
                        )

                    # STATUS_WAIT_CODE — still waiting
                    if text == "STATUS_WAIT_CODE":
                        pass  # continue polling

                    # STATUS_CANCEL — order was cancelled
                    if text == "STATUS_CANCEL":
                        return SMSResult(otp=None, provider=self.provider_name, order_id=order_id)

                except httpx.HTTPStatusError as exc:
                    logger.warning("SMS-Activate poll error: %s", exc.response.status_code)

                await self.async_sleep(interval)

        logger.error("SMS-Activate OTP timed out after %ds", timeout)
        return SMSResult(otp=None, provider=self.provider_name, order_id=order_id)

    async def release_number(self, order_id: str, success: bool = False) -> None:
        # SMS-Activate: status 6 = complete, status 8 = cancel
        status = "6" if success else "8"
        async with httpx.AsyncClient() as client:
            try:
                await client.get(
                    self._base_url,
                    params={
                        "api_key": self._api_key,
                        "action": "setStatus",
                        "id": order_id,
                        "status": status,
                    },
                    timeout=15,
                )
                logger.info("SMS-Activate order %s: status=%s", order_id, status)
            except Exception as exc:
                logger.warning("SMS-Activate release_number failed: %s", exc)

    async def check_balance(self) -> float | None:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    self._base_url,
                    params={"api_key": self._api_key, "action": "getBalance"},
                    timeout=15,
                )
                resp.raise_for_status()
                text = resp.text.strip()
                # Format: ACCESS_BALANCE:AMOUNT
                if text.startswith("ACCESS_BALANCE:"):
                    return float(text.split(":")[1])
                return None
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
