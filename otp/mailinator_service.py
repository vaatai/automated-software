"""Mailinator email OTP service — uses public API to receive OTPs at disposable emails."""

import logging
import random
import re
import time

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://www.mailinator.com/api/v2/domains/public"


class MailinatorService:
    """Provides disposable email inboxes via mailinator.com (no API key required)."""

    async def create_inbox(self) -> dict:
        """Generate a random mailinator inbox."""
        user = f"autoreg{random.randint(10000, 99999)}"
        email = f"{user}@mailinator.com"
        logger.info("Mailinator inbox created: %s", email)
        return {"inbox_id": user, "email_address": email}

    async def get_otp(
        self, inbox_id: str, timeout: int = 60, interval: int = 3
    ) -> str | None:
        """Poll mailinator for an OTP code (4-6 digits)."""
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        f"{BASE_URL}/inboxes/{inbox_id}", timeout=15
                    )
                    if resp.status_code != 200:
                        logger.debug("Mailinator inbox poll HTTP %d", resp.status_code)
                        await _sleep(interval)
                        continue

                    msgs = resp.json().get("msgs", [])
                    if not msgs:
                        await _sleep(interval)
                        continue

                    msg_id = msgs[-1]["id"]
                    resp2 = await client.get(
                        f"{BASE_URL}/messages/{msg_id}", timeout=15
                    )
                    if resp2.status_code != 200:
                        await _sleep(interval)
                        continue

                    body_text = str(resp2.json())
                    match = re.search(r"\b(\d{6})\b", body_text)
                    if match:
                        otp = match.group(1)
                        logger.info("Mailinator OTP for %s: %s", inbox_id, otp)
                        return otp

                    match = re.search(r"\b(\d{4})\b", body_text)
                    if match:
                        otp = match.group(1)
                        logger.info("Mailinator OTP (4-digit) for %s: %s", inbox_id, otp)
                        return otp

            except Exception as exc:
                logger.debug("Mailinator poll error: %s", exc)

            await _sleep(interval)

        logger.warning("Mailinator OTP timeout for %s after %ds", inbox_id, timeout)
        return None

    async def delete_inbox(self, inbox_id: str) -> None:
        """No-op — mailinator public inboxes auto-expire."""
        pass


async def _sleep(seconds: float) -> None:
    import asyncio
    await asyncio.sleep(seconds)
