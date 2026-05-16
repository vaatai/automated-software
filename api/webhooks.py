"""Webhook endpoints for OTP delivery notifications."""

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

# In-memory registry for active webhook handlers.
# Workers register their EmailOTPService instances here so that
# incoming MailSlurp webhooks can resolve the correct Future.
_webhook_registry: dict[str, object] = {}


def register_otp_service(inbox_id: str, service: object) -> None:
    """Register an EmailOTPService for webhook-driven OTP delivery."""
    _webhook_registry[inbox_id] = service


def unregister_otp_service(inbox_id: str) -> None:
    """Remove an EmailOTPService from the webhook registry."""
    _webhook_registry.pop(inbox_id, None)


class MailSlurpWebhookPayload(BaseModel):
    """Expected payload from MailSlurp NEW_EMAIL webhook."""

    inboxId: str
    emailId: str
    subject: str | None = None
    body: str | None = None
    from_address: str | None = None


class WebhookResponse(BaseModel):
    status: str
    inbox_id: str
    otp_found: bool
    otp_code: str | None = None


@router.post(
    "/mailslurp",
    response_model=WebhookResponse,
    summary="MailSlurp webhook receiver",
    description=(
        "Receives NEW_EMAIL webhook notifications from MailSlurp. "
        "Extracts OTP and resolves any waiting polling Futures."
    ),
)
async def mailslurp_webhook(request: Request) -> dict:
    """Handle incoming MailSlurp webhook."""
    raw = await request.json()
    inbox_id = raw.get("inboxId", "")
    email_id = raw.get("emailId", "")

    logger.info("Webhook received: inbox=%s email=%s", inbox_id, email_id)

    if not inbox_id:
        raise HTTPException(status_code=400, detail="Missing inboxId")

    body = raw.get("body", "") or ""
    subject = raw.get("subject", "") or ""

    service = _webhook_registry.get(inbox_id)
    otp: str | None = None
    if service and hasattr(service, "handle_webhook"):
        otp = service.handle_webhook(inbox_id, email_body=body, subject=subject)

    return {
        "status": "processed",
        "inbox_id": inbox_id,
        "otp_found": otp is not None,
        "otp_code": f"***{otp[-2:]}" if otp else None,
    }
