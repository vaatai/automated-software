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


class RentalStatus(str, enum.Enum):
    RENTED = "rented"
    OTP_RECEIVED = "otp_received"
    FINISHED = "finished"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class RentalProvider(str, enum.Enum):
    FIVESIM = "5sim"
    PVAPINS = "pvapins"


class RentalNumber(Base):
    """Tracks phone numbers rented from SMS providers for OTP verification."""

    __tablename__ = "rental_numbers"
    __table_args__ = (
        Index("ix_rental_numbers_registration_id", "registration_id"),
        Index("ix_rental_numbers_provider", "provider"),
        Index("ix_rental_numbers_status", "status"),
        Index("ix_rental_numbers_phone_number", "phone_number"),
        Index("ix_rental_numbers_deleted_at", "deleted_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    registration_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("registrations.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[RentalProvider] = mapped_column(
        Enum(RentalProvider, name="rental_provider"), nullable=False
    )
    status: Mapped[RentalStatus] = mapped_column(
        Enum(RentalStatus, name="rental_status"), default=RentalStatus.RENTED
    )

    # Provider order reference
    order_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone_number: Mapped[str] = mapped_column(String(50), nullable=False)
    country: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # OTP result
    otp_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    raw_sms: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Cost tracking
    cost: Mapped[float | None] = mapped_column(nullable=True)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Timestamps
    rented_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    otp_received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    released_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Soft delete
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    # ── relationships ──────────────────────────────────────
    registration: Mapped[Registration] = relationship(  # noqa: F821
        "Registration", back_populates="rental_numbers"
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def __repr__(self) -> str:
        return f"<RentalNumber(id={self.id}, phone={self.phone_number}, provider={self.provider.value})>"
