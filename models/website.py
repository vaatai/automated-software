from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from configs.database import Base


class WebsiteStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PAUSED = "paused"
    ERROR = "error"


class Website(Base):
    """
    Stores website registration targets and their full configuration.

    ``form_config`` JSON schema supports:
        {
            "registration_url": "https://example.com/register",
            "steps": [                       # multi-step flow support
                {
                    "url": "...",            # optional per-step URL
                    "fields": {
                        "email":    {"selector": "#email",    "type": "email"},
                        "password": {"selector": "#pass",     "type": "password"},
                        "username": {"selector": "#user",     "type": "text"},
                        "phone":    {"selector": "#phone",    "type": "tel"}
                    },
                    "submit_button": {"selector": "#next-btn"}
                }
            ],
            "otp_settings": {
                "email_otp_field":   {"selector": "#email-otp"},
                "email_otp_submit":  {"selector": "#verify-email-btn"},
                "phone_otp_field":   {"selector": "#phone-otp"},
                "phone_otp_submit":  {"selector": "#verify-phone-btn"}
            },
            "captcha_settings": {
                "enabled": false,
                "type": "recaptcha_v2",
                "site_key": "",
                "solver_service": "2captcha"
            },
            "success_indicator": {"selector": ".success-message"},
            "wait_after_submit_ms": 3000
        }
    """

    __tablename__ = "websites"
    __table_args__ = (
        Index("ix_websites_status", "status"),
        Index("ix_websites_deleted_at", "deleted_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[WebsiteStatus] = mapped_column(
        Enum(WebsiteStatus, name="website_status"), default=WebsiteStatus.ACTIVE
    )

    # Full configuration stored as JSON — see docstring for schema
    form_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # OTP requirements
    requires_email_otp: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_mobile_otp: Mapped[bool] = mapped_column(Boolean, default=False)

    # Registration-only mode (skip all OTP verification)
    registration_only_mode: Mapped[bool] = mapped_column(Boolean, default=False)

    # Rate limiting
    max_registrations_per_day: Mapped[int] = mapped_column(Integer, default=100)

    # Optional notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Soft delete
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    # ── relationships ──────────────────────────────────────
    registrations: Mapped[list[Registration]] = relationship(  # noqa: F821
        "Registration", back_populates="website", lazy="selectin"
    )
    daily_limits: Mapped[list[DailyLimit]] = relationship(  # noqa: F821
        "DailyLimit", back_populates="website", lazy="selectin"
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def __repr__(self) -> str:
        return f"<Website(id={self.id}, name={self.name}, status={self.status.value})>"
