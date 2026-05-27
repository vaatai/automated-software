"""PVAPins SMS OTP provider adapter.

Primary SMS provider for Indian numbers. Provides number rental and
SMS polling with country/app selection.

API docs: https://pvapins.com/api_integrate
Base URL: https://api.pvapins.com/user/api/
"""

import asyncio
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

# Map ISO country codes to PVAPins country names
ISO_TO_PVAPINS: dict[str, str] = {
    "IN": "India",
    "US": "USA",
    "GB": "UK",
    "UK": "UK",
    "RU": "Russia",
    "ID": "Indonesia",
    "PK": "Pakistan",
    "BD": "Bangladesh",
    "NP": "Nepal",
    "LK": "Sri Lanka",
    "BR": "Brazil",
    "DE": "Germany",
    "FR": "France",
    "CA": "Canada",
    "AU": "Australia",
    "PH": "Philippines",
    "KR": "South Korea",
    "JP": "Japan",
    "CN": "China",
    "MX": "Mexico",
    "NG": "Nigeria",
    "KE": "Kenya",
    "ZA": "South Africa",
    "EG": "Egypt",
    "TH": "Thailand",
    "VN": "Vietnam",
    "MY": "Malaysia",
    "UA": "Ukraine",
    "PL": "Poland",
    "IT": "Italy",
    "ES": "Spain",
    "NL": "Netherlands",
    "SE": "Sweden",
    "TR": "Turkey",
    "AR": "Argentina",
    "CO": "Colombia",
    "CL": "Chile",
    "PE": "Peru",
}

# Default app names to try for generic number rental (cheap, widely available).
# "Anyother" is a generic catch-all that receives SMS from any sender.
DEFAULT_APPS = ["Anyother", "1xbet1", "telegram", "whatsapp", "other"]


class PVAPinsService(BaseOTPService, SMSProviderAdapter):
    """Primary SMS OTP provider via PVAPins (v2 API).

    Implements both the legacy BaseOTPService interface (for backward compat)
    and the new SMSProviderAdapter interface (for OTPManager).
    """

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or settings.PVAPINS_API_KEY
        self._base_url = settings.PVAPINS_BASE_URL
        # Track rental context for SMS polling
        self._rental_context: dict[str, dict[str, str]] = {}

    @property
    def provider_name(self) -> str:
        return "pvapins"

    @property
    def priority(self) -> int:
        return 1

    def _country_name(self, iso_code: str) -> str:
        """Convert ISO country code to PVAPins country name."""
        return ISO_TO_PVAPINS.get(iso_code.upper(), iso_code)

    # ── SMSProviderAdapter interface ───────────────────────

    async def rent_number(
        self,
        country: str = "US",
        service: str = "any",
        operator: str = "any",
    ) -> RentalResult:
        """Rent a number from PVAPins v2 API.

        Tries multiple app names if service is 'any' or 'opt4'.
        """
        country_name = self._country_name(country)
        if service not in ("any", "opt4", "other"):
            apps_to_try = [service]
        elif country.upper() == "IN":
            # India: only use generic "Anyother" — service-specific apps
            # (1xbet1, telegram, etc.) don't receive SMS from arbitrary senders.
            apps_to_try = ["Anyother"]
        else:
            apps_to_try = DEFAULT_APPS
        last_error: str = ""

        async with httpx.AsyncClient() as client:
            for app in apps_to_try:
                try:
                    resp = await client.get(
                        f"{self._base_url}/get_number.php",
                        params={
                            "customer": self._api_key,
                            "app": app,
                            "country": country_name,
                        },
                        timeout=30,
                    )
                    body = resp.text.strip()

                    if resp.status_code != 200:
                        last_error = f"HTTP {resp.status_code}"
                        logger.debug("PVAPins %s/%s: %s", country_name, app, last_error)
                        continue

                    if "not found" in body.lower():
                        last_error = body
                        logger.debug("PVAPins %s/%s: %s", country_name, app, body)
                        continue

                    if "no free channels" in body.lower() or "not available" in body.lower():
                        last_error = body
                        logger.debug("PVAPins %s/%s: %s", country_name, app, body)
                        continue

                    if "insufficient" in body.lower() or "balance" in body.lower():
                        raise ProviderError(self.provider_name, f"Insufficient balance: {body}")

                    # Success — response is the phone number as plain text
                    phone_number = body
                    if not phone_number or not phone_number[0].isdigit():
                        last_error = f"Unexpected response: {body[:100]}"
                        logger.debug("PVAPins %s/%s: %s", country_name, app, last_error)
                        continue

                    logger.info("PVAPins rented number: %s (app=%s, country=%s)", phone_number, app, country_name)

                    # Store context for SMS polling (new API needs number+country+app)
                    self._rental_context[phone_number] = {
                        "country": country_name,
                        "app": app,
                    }

                    return RentalResult(
                        order_id=phone_number,
                        phone_number=phone_number,
                        provider=self.provider_name,
                        country=country,
                        service=app,
                    )

                except httpx.HTTPStatusError as exc:
                    last_error = f"HTTP {exc.response.status_code}"
                    logger.debug("PVAPins %s/%s error: %s", country_name, app, last_error)
                except ProviderError:
                    raise
                except Exception as exc:
                    last_error = str(exc)
                    logger.debug("PVAPins %s/%s exception: %s", country_name, app, exc)

        raise NumberUnavailableError(self.provider_name, country, service)

    async def poll_for_otp(
        self,
        order_id: str,
        timeout: int = 120,
        interval: int = 5,
        known_otp: str | None = None,
    ) -> SMSResult:
        """Poll for OTP using the v2 get_sms.php endpoint."""
        start = time.monotonic()
        phone_number = order_id

        ctx = self._rental_context.get(phone_number, {})
        country_name = ctx.get("country", "India")
        app = ctx.get("app", "1xbet1")

        async with httpx.AsyncClient() as client:
            while time.monotonic() - start < timeout:
                try:
                    resp = await client.get(
                        f"{self._base_url}/get_sms.php",
                        params={
                            "customer": self._api_key,
                            "number": phone_number,
                            "country": country_name,
                            "app": app,
                        },
                        timeout=15,
                    )
                    body = resp.text.strip()

                    # "You have not received any code yet." = still waiting
                    if "not received" in body.lower() or "wait" in body.lower():
                        pass  # keep polling
                    elif body and body[0].isdigit():
                        # Got OTP — response is the code as plain text
                        otp = self.extract_otp(body)
                        if otp and otp != known_otp:
                            logger.info("PVAPins OTP received: %s", otp)
                            return SMSResult(
                                otp=otp,
                                raw_message=body,
                                provider=self.provider_name,
                                order_id=order_id,
                            )
                    elif "error" in body.lower() or "expired" in body.lower():
                        logger.warning("PVAPins SMS error: %s", body)
                        return SMSResult(otp=None, provider=self.provider_name, order_id=order_id)

                except Exception as exc:
                    logger.warning("PVAPins poll error: %s", exc)

                await asyncio.sleep(interval)

        logger.error("PVAPins OTP timed out after %ds for %s", timeout, phone_number)
        return SMSResult(otp=None, provider=self.provider_name, order_id=order_id)

    async def release_number(self, order_id: str, success: bool = False) -> None:
        """Release/reject a number.

        The v2 API has no explicit "complete" endpoint — numbers
        auto-complete after OTP receipt.  We only call reject.php
        when the number was *not* used successfully.
        """
        phone_number = order_id
        ctx = self._rental_context.pop(phone_number, {})
        country_name = ctx.get("country", "India")
        app = ctx.get("app", "1xbet1")

        if success:
            logger.info("PVAPins number %s completed (auto-finalized by provider)", phone_number)
            return

        async with httpx.AsyncClient() as client:
            try:
                await client.get(
                    f"{self._base_url}/reject.php",
                    params={
                        "customer": self._api_key,
                        "number": phone_number,
                        "country": country_name,
                        "app": app,
                    },
                    timeout=15,
                )
                logger.info("PVAPins rejected number %s", phone_number)
            except Exception as exc:
                logger.warning("PVAPins release_number failed: %s", exc)

    async def check_balance(self) -> float | None:
        """Check account balance via get_balance.php."""
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{self._base_url}/get_balance.php",
                    params={"customer": self._api_key},
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return float(data.get("balance", 0))
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
        known_otp = str(kwargs.get("known_otp", "") or "") or None
        result = await self.poll_for_otp(order_id, timeout=timeout, interval=interval, known_otp=known_otp)
        return result.otp
