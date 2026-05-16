"""Email OTP verification service — full lifecycle management.

Provides a high-level abstraction over MailSlurp for:
- Temporary inbox creation and cleanup
- Async inbox polling with configurable timeouts
- Parallel inbox polling for multiple registrations
- Webhook-driven OTP delivery
- Robust OTP extraction with configurable regex patterns
- Structured event logging
- Worker-safe execution (no shared mutable state)
"""

import asyncio
import logging
import time

import httpx

from configs.settings import settings
from otp.otp_events import OTPEventLogger, OTPEventType
from otp.otp_parser import OTPParser, OTPPattern

logger = logging.getLogger(__name__)

MAILSLURP_BASE = "https://api.mailslurp.com"


class EmailInbox:
    """Represents a temporary MailSlurp inbox with its lifecycle state."""

    def __init__(self, inbox_id: str, email_address: str) -> None:
        self.inbox_id = inbox_id
        self.email_address = email_address
        self.otp: str | None = None
        self.is_deleted = False

    def __repr__(self) -> str:
        return f"<EmailInbox(id={self.inbox_id}, email={self.email_address})>"


class EmailOTPService:
    """Full-lifecycle email OTP service with event logging and parallel support.

    Each instance is safe to use from a single async task / Celery worker.
    For parallel polling, use :meth:`poll_multiple_inboxes`.

    Usage::

        service = EmailOTPService(registration_id=42)
        inbox = await service.create_inbox()
        # ... use inbox.email_address in registration form ...
        otp = await service.poll_for_otp(inbox.inbox_id)
        if otp:
            # submit OTP to form
            service.events.log(OTPEventType.OTP_SUBMITTED, otp_code=otp)
        await service.delete_inbox(inbox.inbox_id)
    """

    def __init__(
        self,
        api_key: str | None = None,
        registration_id: int | None = None,
        poll_timeout: int | None = None,
        poll_interval: int | None = None,
        max_retries: int = 3,
        custom_patterns: list[OTPPattern] | None = None,
    ) -> None:
        self._api_key = api_key or settings.MAILSLURP_API_KEY
        self._headers = {"x-api-key": self._api_key}
        self._poll_timeout = poll_timeout or settings.OTP_POLL_TIMEOUT_SECONDS
        self._poll_interval = poll_interval or settings.OTP_POLL_INTERVAL_SECONDS
        self._max_retries = max_retries
        self._parser = OTPParser(custom_patterns=custom_patterns)
        self.events = OTPEventLogger(registration_id=registration_id)
        self._inboxes: dict[str, EmailInbox] = {}
        self._webhook_otps: dict[str, asyncio.Future[str]] = {}

    # ── inbox lifecycle ────────────────────────────────────

    async def create_inbox(
        self,
        name: str | None = None,
        expires_in_ms: int = 600_000,
    ) -> EmailInbox:
        """Create a temporary MailSlurp inbox.

        Args:
            name: Optional human-readable name for the inbox.
            expires_in_ms: Auto-expiry time (default 10 minutes).

        Returns:
            EmailInbox with inbox_id and email_address.
        """
        params: dict = {"expiresIn": expires_in_ms}
        if name:
            params["name"] = name

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{MAILSLURP_BASE}/inboxes",
                headers=self._headers,
                params=params,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

        inbox = EmailInbox(
            inbox_id=data["id"], email_address=data["emailAddress"]
        )
        self._inboxes[inbox.inbox_id] = inbox

        self.events.log(
            OTPEventType.INBOX_CREATED,
            inbox_id=inbox.inbox_id,
            email_address=inbox.email_address,
        )
        return inbox

    async def delete_inbox(self, inbox_id: str) -> None:
        """Delete a temporary inbox and mark it as cleaned up."""
        async with httpx.AsyncClient() as client:
            try:
                await client.delete(
                    f"{MAILSLURP_BASE}/inboxes/{inbox_id}",
                    headers=self._headers,
                    timeout=15,
                )
                self.events.log(OTPEventType.INBOX_DELETED, inbox_id=inbox_id)
            except Exception as exc:
                self.events.log(
                    OTPEventType.ERROR,
                    inbox_id=inbox_id,
                    error=f"Failed to delete inbox: {exc}",
                )

        inbox = self._inboxes.get(inbox_id)
        if inbox:
            inbox.is_deleted = True

    async def cleanup_all_inboxes(self) -> None:
        """Delete all inboxes created by this service instance."""
        tasks = [
            self.delete_inbox(inbox_id)
            for inbox_id, inbox in self._inboxes.items()
            if not inbox.is_deleted
        ]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    # ── OTP polling ────────────────────────────────────────

    async def poll_for_otp(
        self,
        inbox_id: str,
        timeout: int | None = None,
        interval: int | None = None,
    ) -> str | None:
        """Poll a MailSlurp inbox until an OTP email arrives.

        Uses the ``waitForLatestEmail`` endpoint with configurable
        timeout and polling interval. Extracts OTP via the parser.

        Returns:
            The OTP code string, or None on timeout.
        """
        poll_timeout = timeout or self._poll_timeout
        poll_interval = interval or self._poll_interval
        start = time.monotonic()
        attempt = 0

        self.events.log(
            OTPEventType.POLL_STARTED,
            inbox_id=inbox_id,
            details={"timeout": poll_timeout, "interval": poll_interval},
        )

        async with httpx.AsyncClient() as client:
            while time.monotonic() - start < poll_timeout:
                attempt += 1
                self.events.log(
                    OTPEventType.POLL_ATTEMPT,
                    inbox_id=inbox_id,
                    attempt=attempt,
                )

                try:
                    resp = await client.get(
                        f"{MAILSLURP_BASE}/waitForLatestEmail",
                        params={
                            "inboxId": inbox_id,
                            "timeout": poll_interval * 1000,
                            "unreadOnly": True,
                        },
                        headers=self._headers,
                        timeout=poll_interval + 10,
                    )

                    if resp.status_code == 200:
                        data = resp.json()
                        self.events.log(
                            OTPEventType.EMAIL_RECEIVED,
                            inbox_id=inbox_id,
                            details={
                                "subject": data.get("subject", ""),
                                "from": data.get("from", ""),
                            },
                        )

                        result = self._parser.extract_from_email(
                            body=data.get("body"),
                            subject=data.get("subject"),
                            html_body=data.get("htmlBody"),
                        )

                        if result.otp:
                            elapsed_ms = int((time.monotonic() - start) * 1000)
                            self.events.log(
                                OTPEventType.OTP_EXTRACTED,
                                inbox_id=inbox_id,
                                otp_code=result.otp,
                                pattern_name=result.pattern_name,
                                duration_ms=elapsed_ms,
                                details={
                                    "source": result.source,
                                    "confidence": result.confidence,
                                },
                            )
                            inbox = self._inboxes.get(inbox_id)
                            if inbox:
                                inbox.otp = result.otp
                            return result.otp

                except httpx.TimeoutException:
                    logger.debug("Poll attempt %d timed out for inbox %s", attempt, inbox_id)
                except httpx.HTTPStatusError as exc:
                    self.events.log(
                        OTPEventType.ERROR,
                        inbox_id=inbox_id,
                        attempt=attempt,
                        error=f"HTTP {exc.response.status_code}",
                    )

                await asyncio.sleep(poll_interval)

        elapsed_ms = int((time.monotonic() - start) * 1000)
        self.events.log(
            OTPEventType.TIMEOUT,
            inbox_id=inbox_id,
            duration_ms=elapsed_ms,
            details={"attempts": attempt},
        )
        return None

    async def poll_multiple_inboxes(
        self,
        inbox_ids: list[str],
        timeout: int | None = None,
        interval: int | None = None,
    ) -> dict[str, str | None]:
        """Poll multiple inboxes in parallel.

        Returns a dict mapping inbox_id → OTP code (or None).
        """
        tasks = [
            self.poll_for_otp(inbox_id, timeout=timeout, interval=interval)
            for inbox_id in inbox_ids
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output: dict[str, str | None] = {}
        for inbox_id, result in zip(inbox_ids, results):
            if isinstance(result, Exception):
                self.events.log(
                    OTPEventType.ERROR,
                    inbox_id=inbox_id,
                    error=str(result),
                )
                output[inbox_id] = None
            else:
                output[inbox_id] = result
        return output

    # ── webhook support ────────────────────────────────────

    def register_webhook_listener(self, inbox_id: str) -> asyncio.Future[str]:
        """Register a Future that will be resolved when a webhook delivers an OTP.

        The webhook endpoint should call :meth:`handle_webhook` when
        MailSlurp sends a new-email notification.

        Returns:
            An asyncio.Future that resolves to the OTP string.
        """
        loop = asyncio.get_running_loop()
        future: asyncio.Future[str] = loop.create_future()
        self._webhook_otps[inbox_id] = future
        return future

    def handle_webhook(self, inbox_id: str, email_body: str, subject: str = "") -> str | None:
        """Process an incoming webhook notification from MailSlurp.

        Extracts the OTP and resolves any waiting Future.

        Returns:
            The extracted OTP code, or None.
        """
        self.events.log(
            OTPEventType.WEBHOOK_RECEIVED,
            inbox_id=inbox_id,
            details={"subject": subject},
        )

        result = self._parser.extract_from_email(
            body=email_body, subject=subject
        )

        if result.otp:
            self.events.log(
                OTPEventType.OTP_EXTRACTED,
                inbox_id=inbox_id,
                otp_code=result.otp,
                pattern_name=result.pattern_name,
            )
            future = self._webhook_otps.pop(inbox_id, None)
            if future and not future.done():
                future.set_result(result.otp)
            inbox = self._inboxes.get(inbox_id)
            if inbox:
                inbox.otp = result.otp
            return result.otp

        return None

    async def wait_for_webhook_otp(
        self,
        inbox_id: str,
        timeout: int | None = None,
    ) -> str | None:
        """Wait for an OTP to be delivered via webhook.

        Falls back to polling if the webhook doesn't deliver within timeout.
        """
        poll_timeout = timeout or self._poll_timeout
        future = self.register_webhook_listener(inbox_id)

        try:
            return await asyncio.wait_for(future, timeout=poll_timeout)
        except asyncio.TimeoutError:
            self._webhook_otps.pop(inbox_id, None)
            self.events.log(
                OTPEventType.TIMEOUT,
                inbox_id=inbox_id,
                details={"mode": "webhook"},
            )
            logger.warning(
                "Webhook OTP timed out for inbox %s, falling back to polling",
                inbox_id,
            )
            return await self.poll_for_otp(inbox_id, timeout=poll_timeout // 2)

    # ── utility ────────────────────────────────────────────

    def get_inbox(self, inbox_id: str) -> EmailInbox | None:
        return self._inboxes.get(inbox_id)

    def get_events(self) -> list[dict]:
        return self.events.to_dicts()
