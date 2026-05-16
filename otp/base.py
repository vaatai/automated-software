import asyncio
import re
from abc import ABC, abstractmethod


class BaseOTPService(ABC):
    """Abstract base for all OTP providers."""

    @abstractmethod
    async def get_otp(self, **kwargs: object) -> str | None:
        """Wait for and return the OTP code, or None on timeout."""

    @staticmethod
    def extract_otp(text: str) -> str | None:
        """Extract an OTP code from raw text using common patterns."""
        patterns = [
            r"(?:code|otp|pin|verification)[:\s]*(\d{4,8})",
            r"(\d{4,8})\s*(?:is your|is the)",
            r"\b(\d{6})\b",
            r"\b(\d{4})\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    @staticmethod
    async def async_sleep(seconds: float) -> None:
        await asyncio.sleep(seconds)
