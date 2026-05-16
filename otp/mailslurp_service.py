import logging
import time

import httpx

from configs.settings import settings
from otp.base import BaseOTPService

logger = logging.getLogger(__name__)

MAILSLURP_BASE = "https://api.mailslurp.com"


class MailSlurpService(BaseOTPService):
    """Email OTP verification via MailSlurp."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.MAILSLURP_API_KEY
        self.headers = {"x-api-key": self.api_key}

    async def create_inbox(self) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{MAILSLURP_BASE}/inboxes", headers=self.headers, timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info("Created inbox: %s", data["emailAddress"])
            return {"inbox_id": data["id"], "email_address": data["emailAddress"]}

    async def get_otp(self, *, inbox_id: str, **kwargs: object) -> str | None:
        """Poll the inbox until an OTP arrives or timeout."""
        timeout = int(kwargs.get("timeout", settings.OTP_POLL_TIMEOUT_SECONDS) or 0)
        interval = int(kwargs.get("interval", settings.OTP_POLL_INTERVAL_SECONDS) or 0)
        start = time.time()

        async with httpx.AsyncClient() as client:
            while time.time() - start < timeout:
                try:
                    resp = await client.get(
                        f"{MAILSLURP_BASE}/waitForLatestEmail",
                        params={
                            "inboxId": inbox_id,
                            "timeout": interval * 1000,
                            "unreadOnly": True,
                        },
                        headers=self.headers,
                        timeout=interval + 10,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        otp = self.extract_otp(data.get("body", "")) or self.extract_otp(
                            data.get("subject", "")
                        )
                        if otp:
                            logger.info("Email OTP extracted: %s", otp)
                            return otp
                except httpx.TimeoutException:
                    logger.debug("Inbox poll timeout, retrying…")
                except httpx.HTTPStatusError as exc:
                    logger.warning("MailSlurp error: %s", exc.response.status_code)

                await self.async_sleep(interval)

        logger.error("Email OTP timed out after %ds", timeout)
        return None

    async def delete_inbox(self, inbox_id: str) -> None:
        async with httpx.AsyncClient() as client:
            try:
                await client.delete(
                    f"{MAILSLURP_BASE}/inboxes/{inbox_id}",
                    headers=self.headers,
                    timeout=15,
                )
            except Exception as exc:
                logger.warning("Failed to delete inbox %s: %s", inbox_id, exc)
