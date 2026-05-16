"""MailSlurp service — thin wrapper over EmailOTPService for backward compatibility.

New code should use :class:`EmailOTPService` directly for full
event logging, webhook support, and parallel polling.
"""

import logging

from otp.base import BaseOTPService
from otp.email_otp_service import EmailOTPService

logger = logging.getLogger(__name__)


class MailSlurpService(BaseOTPService):
    """Email OTP verification via MailSlurp.

    Wraps :class:`EmailOTPService` to preserve the existing API contract
    used by :class:`RegistrationBot`.
    """

    def __init__(
        self,
        api_key: str | None = None,
        registration_id: int | None = None,
    ) -> None:
        self._service = EmailOTPService(
            api_key=api_key, registration_id=registration_id
        )

    @property
    def email_otp_service(self) -> EmailOTPService:
        """Access the underlying EmailOTPService for advanced features."""
        return self._service

    async def create_inbox(self) -> dict:
        inbox = await self._service.create_inbox()
        return {"inbox_id": inbox.inbox_id, "email_address": inbox.email_address}

    async def get_otp(self, *, inbox_id: str, **kwargs: object) -> str | None:
        timeout = int(kwargs.get("timeout", 0) or 0) or None
        interval = int(kwargs.get("interval", 0) or 0) or None
        return await self._service.poll_for_otp(
            inbox_id, timeout=timeout, interval=interval
        )

    async def delete_inbox(self, inbox_id: str) -> None:
        await self._service.delete_inbox(inbox_id)

    def get_events(self) -> list[dict]:
        """Get the OTP event audit trail."""
        return self._service.get_events()
