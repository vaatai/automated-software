from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from configs.database import Base


class OTPProvider(str, enum.Enum):
    MAILSLURP = "mailslurp"
    FIVESIM = "5sim"
    PVAPINS = "pvapins"


class OTPType(str, enum.Enum):
    EMAIL = "email"
    SMS = "sms"


class OTPConfig(Base):
    __tablename__ = "otp_configs"
    __table_args__ = (
        Index("ix_otp_configs_provider_type", "provider", "otp_type"),
        Index("ix_otp_configs_website_id", "website_id"),
        Index("ix_otp_configs_deleted_at", "deleted_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Optional per-website override; NULL = global config
    website_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("websites.id", ondelete="CASCADE"), nullable=True
    )

    provider: Mapped[OTPProvider] = mapped_column(
        Enum(OTPProvider, name="otp_provider"), nullable=False
    )
    otp_type: Mapped[OTPType] = mapped_column(
        Enum(OTPType, name="otp_type"), nullable=False
    )
    api_key: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    priority: Mapped[int] = mapped_column(Integer, default=1)

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
    website: Mapped[Website | None] = relationship("Website")  # noqa: F821

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def __repr__(self) -> str:
        return f"<OTPConfig(id={self.id}, provider={self.provider.value}, type={self.otp_type.value})>"
