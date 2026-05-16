"""Abstract SMS provider adapter interface for mobile OTP verification.

All SMS providers (5SIM, PVAPins, SMS-Activate) implement this interface
so the OTPManager can switch between them transparently.
"""

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass


class ProviderStatus(str, enum.Enum):
    """Provider operational status."""

    AVAILABLE = "available"
    NO_NUMBERS = "no_numbers"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class RentalResult:
    """Result of renting a phone number."""

    order_id: str
    phone_number: str
    provider: str
    country: str
    service: str


@dataclass
class SMSResult:
    """Result of OTP extraction from SMS."""

    otp: str | None
    raw_message: str | None = None
    provider: str | None = None
    order_id: str | None = None


class SMSProviderAdapter(ABC):
    """Abstract base for all SMS OTP provider adapters.

    Each provider must implement:
    - rent_number: acquire a temporary phone number
    - poll_for_otp: wait for and extract OTP from incoming SMS
    - release_number: release the rented number (finish or cancel)
    - check_balance: optional balance check
    - get_status: check if provider is operational
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique provider identifier."""

    @property
    @abstractmethod
    def priority(self) -> int:
        """Provider priority (lower = preferred). Used for fallback ordering."""

    @abstractmethod
    async def rent_number(
        self,
        country: str = "any",
        service: str = "any",
        operator: str = "any",
    ) -> RentalResult:
        """Rent a temporary phone number.

        Raises:
            NumberUnavailableError: No numbers available for this country/service.
            ProviderError: API error from the provider.
        """

    @abstractmethod
    async def poll_for_otp(
        self,
        order_id: str,
        timeout: int = 120,
        interval: int = 5,
    ) -> SMSResult:
        """Poll for an incoming OTP SMS.

        Returns SMSResult with otp=None on timeout.
        """

    @abstractmethod
    async def release_number(self, order_id: str, success: bool = False) -> None:
        """Release a rented number.

        Args:
            order_id: The rental order ID.
            success: If True, marks the order as completed; otherwise cancels.
        """

    async def check_balance(self) -> float | None:
        """Check account balance. Returns None if not supported."""
        return None

    async def get_status(self) -> ProviderStatus:
        """Check if the provider is operational."""
        return ProviderStatus.AVAILABLE


class NumberUnavailableError(Exception):
    """Raised when no numbers are available for the requested country/service."""

    def __init__(self, provider: str, country: str, service: str) -> None:
        self.provider = provider
        self.country = country
        self.service = service
        super().__init__(
            f"No numbers available on {provider} for country={country}, service={service}"
        )


class ProviderError(Exception):
    """General provider API error."""

    def __init__(self, provider: str, message: str, status_code: int | None = None) -> None:
        self.provider = provider
        self.status_code = status_code
        super().__init__(f"[{provider}] {message}")
