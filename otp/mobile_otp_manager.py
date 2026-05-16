"""Mobile OTP Manager — orchestrates SMS providers with automatic fallback.

Provides a single entry point for mobile OTP verification:
1. Tries the primary provider (5SIM)
2. Falls back to secondary (PVAPins) if primary fails
3. Falls back to backup (SMS-Activate) if secondary fails
4. Handles inventory unavailable, rate limits, and errors
5. Supports concurrent rentals across multiple registrations
6. Configurable per-registration country/service selection

Usage::

    manager = MobileOTPManager()
    rental = await manager.rent_and_verify(
        country="US",
        service="google",
        timeout=120,
    )
    if rental.otp:
        # use rental.otp in the registration form
        ...
"""

import asyncio
import logging
from dataclasses import dataclass, field

from otp.fivesim_service import FiveSimService
from otp.pvapins_service import PVAPinsService
from otp.sms_provider import (
    NumberUnavailableError,
    ProviderError,
    ProviderStatus,
    RentalResult,
    SMSProviderAdapter,
    SMSResult,
)
from otp.smsactivate_service import SMSActivateService

logger = logging.getLogger(__name__)


@dataclass
class MobileOTPResult:
    """Complete result of a mobile OTP verification attempt."""

    success: bool
    otp: str | None = None
    phone_number: str | None = None
    provider: str | None = None
    order_id: str | None = None
    attempts: list[dict] = field(default_factory=list)
    error: str | None = None


class MobileOTPManager:
    """Orchestrates multiple SMS providers with automatic fallback.

    Providers are tried in priority order. If a provider fails due to
    number unavailability or API errors, the next provider is tried.

    Thread/worker-safe: each instance manages its own state.
    """

    def __init__(
        self,
        providers: list[SMSProviderAdapter] | None = None,
        max_retries: int = 2,
        poll_timeout: int = 120,
        poll_interval: int = 5,
    ) -> None:
        """Initialize with optional custom provider list.

        Args:
            providers: Custom provider list (sorted by priority).
                       Defaults to [5SIM, PVAPins, SMS-Activate].
            max_retries: Retries per provider before moving to next.
            poll_timeout: Default OTP polling timeout in seconds.
            poll_interval: Default polling interval in seconds.
        """
        if providers:
            self._providers = sorted(providers, key=lambda p: p.priority)
        else:
            self._providers: list[SMSProviderAdapter] = [
                FiveSimService(),
                PVAPinsService(),
                SMSActivateService(),
            ]
        self._max_retries = max_retries
        self._poll_timeout = poll_timeout
        self._poll_interval = poll_interval
        self._active_rentals: dict[str, tuple[SMSProviderAdapter, RentalResult]] = {}

    @property
    def providers(self) -> list[str]:
        return [p.provider_name for p in self._providers]

    # ── core workflow ──────────────────────────────────────

    async def rent_number(
        self,
        country: str = "any",
        service: str = "any",
        operator: str = "any",
        preferred_provider: str | None = None,
    ) -> RentalResult:
        """Rent a number with automatic provider fallback.

        Tries each provider in priority order until one succeeds.

        Args:
            country: Target country code.
            service: Target service identifier.
            operator: Operator preference.
            preferred_provider: Skip to this provider first (if available).

        Returns:
            RentalResult with order_id and phone_number.

        Raises:
            NumberUnavailableError: All providers exhausted.
        """
        providers = self._get_provider_order(preferred_provider)

        for provider in providers:
            status = await provider.get_status()
            if status in (ProviderStatus.DISABLED, ProviderStatus.ERROR):
                logger.info(
                    "Skipping %s (status=%s)", provider.provider_name, status.value
                )
                continue

            for attempt in range(1, self._max_retries + 1):
                try:
                    rental = await provider.rent_number(
                        country=country, service=service, operator=operator
                    )
                    self._active_rentals[rental.order_id] = (provider, rental)
                    logger.info(
                        "Rented number via %s: %s (attempt %d)",
                        provider.provider_name,
                        rental.phone_number,
                        attempt,
                    )
                    return rental
                except NumberUnavailableError:
                    logger.warning(
                        "%s: no numbers for country=%s service=%s",
                        provider.provider_name,
                        country,
                        service,
                    )
                    break  # move to next provider
                except ProviderError as exc:
                    logger.warning(
                        "%s attempt %d failed: %s",
                        provider.provider_name,
                        attempt,
                        exc,
                    )
                    if attempt < self._max_retries:
                        await asyncio.sleep(2 * attempt)  # brief backoff
                except Exception as exc:
                    logger.error(
                        "%s unexpected error: %s", provider.provider_name, exc
                    )
                    break  # move to next provider

        raise NumberUnavailableError(
            "all_providers",
            country,
            service,
        )

    async def poll_for_otp(
        self,
        order_id: str,
        timeout: int | None = None,
        interval: int | None = None,
    ) -> SMSResult:
        """Poll for OTP on an active rental.

        Automatically routes to the correct provider based on order_id.
        """
        entry = self._active_rentals.get(order_id)
        if not entry:
            raise ValueError(f"No active rental found for order_id={order_id}")

        provider, rental = entry
        poll_timeout = timeout or self._poll_timeout
        poll_interval = interval or self._poll_interval

        return await provider.poll_for_otp(
            order_id, timeout=poll_timeout, interval=poll_interval
        )

    async def release_number(self, order_id: str, success: bool = False) -> None:
        """Release a rented number (finish or cancel)."""
        entry = self._active_rentals.pop(order_id, None)
        if not entry:
            logger.warning("No active rental for order_id=%s", order_id)
            return

        provider, rental = entry
        await provider.release_number(order_id, success=success)

    # ── high-level convenience ─────────────────────────────

    async def rent_and_verify(
        self,
        country: str = "any",
        service: str = "any",
        operator: str = "any",
        timeout: int | None = None,
        interval: int | None = None,
        preferred_provider: str | None = None,
    ) -> MobileOTPResult:
        """Full workflow: rent number → poll for OTP → release.

        Tries multiple providers with fallback if OTP is not received.

        Returns:
            MobileOTPResult with success flag, OTP, phone, provider info.
        """
        providers = self._get_provider_order(preferred_provider)
        poll_timeout = timeout or self._poll_timeout
        poll_interval = interval or self._poll_interval
        attempts: list[dict] = []

        for provider in providers:
            status = await provider.get_status()
            if status in (ProviderStatus.DISABLED, ProviderStatus.ERROR):
                attempts.append({
                    "provider": provider.provider_name,
                    "status": "skipped",
                    "reason": status.value,
                })
                continue

            try:
                rental = await provider.rent_number(
                    country=country, service=service, operator=operator
                )
                self._active_rentals[rental.order_id] = (provider, rental)
            except (NumberUnavailableError, ProviderError) as exc:
                attempts.append({
                    "provider": provider.provider_name,
                    "status": "rent_failed",
                    "error": str(exc),
                })
                continue

            # Poll for OTP (ensure number is released even on unexpected errors)
            try:
                sms_result = await provider.poll_for_otp(
                    rental.order_id, timeout=poll_timeout, interval=poll_interval
                )
            except Exception as exc:
                logger.error(
                    "%s: poll_for_otp crashed: %s", provider.provider_name, exc
                )
                sms_result = SMSResult(
                    otp=None, provider=provider.provider_name, order_id=rental.order_id
                )

            if sms_result.otp:
                await provider.release_number(rental.order_id, success=True)
                self._active_rentals.pop(rental.order_id, None)
                attempts.append({
                    "provider": provider.provider_name,
                    "status": "success",
                    "phone": rental.phone_number,
                })
                return MobileOTPResult(
                    success=True,
                    otp=sms_result.otp,
                    phone_number=rental.phone_number,
                    provider=provider.provider_name,
                    order_id=rental.order_id,
                    attempts=attempts,
                )
            else:
                await provider.release_number(rental.order_id, success=False)
                self._active_rentals.pop(rental.order_id, None)
                attempts.append({
                    "provider": provider.provider_name,
                    "status": "otp_timeout",
                    "phone": rental.phone_number,
                })
                logger.warning(
                    "%s: OTP not received for %s, trying next provider",
                    provider.provider_name,
                    rental.phone_number,
                )

        return MobileOTPResult(
            success=False,
            attempts=attempts,
            error="All providers exhausted without receiving OTP",
        )

    async def rent_multiple(
        self,
        count: int,
        country: str = "any",
        service: str = "any",
    ) -> list[RentalResult]:
        """Rent multiple numbers concurrently.

        Uses asyncio.gather for parallel acquisition.
        Returns list of successful rentals (may be fewer than count).
        """
        tasks = [
            self.rent_number(country=country, service=service)
            for _ in range(count)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        rentals: list[RentalResult] = []
        for result in results:
            if isinstance(result, RentalResult):
                rentals.append(result)
            elif isinstance(result, Exception):
                logger.warning("Concurrent rent failed: %s", result)

        return rentals

    async def cleanup_all(self) -> None:
        """Release all active rentals (cancel)."""
        order_ids = list(self._active_rentals.keys())
        for order_id in order_ids:
            await self.release_number(order_id, success=False)

    # ── provider health ────────────────────────────────────

    async def check_all_providers(self) -> dict[str, str]:
        """Check status of all providers."""
        statuses: dict[str, str] = {}
        for provider in self._providers:
            status = await provider.get_status()
            statuses[provider.provider_name] = status.value
        return statuses

    async def get_balances(self) -> dict[str, float | None]:
        """Get balance for all providers."""
        balances: dict[str, float | None] = {}
        for provider in self._providers:
            balances[provider.provider_name] = await provider.check_balance()
        return balances

    # ── internal ───────────────────────────────────────────

    def _get_provider_order(
        self, preferred: str | None = None
    ) -> list[SMSProviderAdapter]:
        """Get providers in execution order, optionally prioritizing one."""
        if not preferred:
            return list(self._providers)

        preferred_list: list[SMSProviderAdapter] = []
        others: list[SMSProviderAdapter] = []
        for p in self._providers:
            if p.provider_name == preferred:
                preferred_list.append(p)
            else:
                others.append(p)
        return preferred_list + others
