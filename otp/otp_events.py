"""Structured OTP event logging for audit trails and debugging."""

import enum
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class OTPEventType(str, enum.Enum):
    INBOX_CREATED = "inbox_created"
    INBOX_DELETED = "inbox_deleted"
    POLL_STARTED = "poll_started"
    POLL_ATTEMPT = "poll_attempt"
    EMAIL_RECEIVED = "email_received"
    OTP_EXTRACTED = "otp_extracted"
    OTP_SUBMITTED = "otp_submitted"
    OTP_VERIFIED = "otp_verified"
    OTP_FAILED = "otp_failed"
    WEBHOOK_RECEIVED = "webhook_received"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class OTPEvent:
    """A single OTP lifecycle event."""

    event_type: OTPEventType
    registration_id: int | None = None
    inbox_id: str | None = None
    email_address: str | None = None
    otp_code: str | None = None
    pattern_name: str | None = None
    attempt: int = 0
    duration_ms: int = 0
    error: str | None = None
    details: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class OTPEventLogger:
    """Collects and logs OTP events for a registration session.

    Usage::

        event_logger = OTPEventLogger(registration_id=42)
        event_logger.log(OTPEventType.INBOX_CREATED, inbox_id="abc", email_address="x@y.com")
        ...
        events = event_logger.events  # full audit trail
    """

    def __init__(self, registration_id: int | None = None) -> None:
        self.registration_id = registration_id
        self._events: list[OTPEvent] = []

    @property
    def events(self) -> list[OTPEvent]:
        return self._events.copy()

    def log(self, event_type: OTPEventType, **kwargs: object) -> OTPEvent:
        """Create and record an OTP event."""
        event = OTPEvent(
            event_type=event_type,
            registration_id=self.registration_id,
            **kwargs,  # type: ignore[arg-type]
        )
        self._events.append(event)

        log_msg = (
            f"[OTP] reg={self.registration_id} event={event_type.value}"
        )
        if event.inbox_id:
            log_msg += f" inbox={event.inbox_id}"
        if event.otp_code:
            log_msg += f" otp=***{event.otp_code[-2:]}"
        if event.error:
            log_msg += f" error={event.error}"
        if event.duration_ms:
            log_msg += f" duration={event.duration_ms}ms"

        if event_type in (OTPEventType.ERROR, OTPEventType.OTP_FAILED):
            logger.error(log_msg)
        elif event_type == OTPEventType.TIMEOUT:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

        return event

    def to_dicts(self) -> list[dict]:
        """Serialize all events for storage or API response."""
        result = []
        for e in self._events:
            result.append({
                "event_type": e.event_type.value,
                "registration_id": e.registration_id,
                "inbox_id": e.inbox_id,
                "email_address": e.email_address,
                "otp_code": f"***{e.otp_code[-2:]}" if e.otp_code else None,
                "pattern_name": e.pattern_name,
                "attempt": e.attempt,
                "duration_ms": e.duration_ms,
                "error": e.error,
                "timestamp": e.timestamp.isoformat(),
            })
        return result
