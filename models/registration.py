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


class RegistrationStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    EMAIL_OTP_PENDING = "email_otp_pending"
    MOBILE_OTP_PENDING = "mobile_otp_pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DAILY_LIMIT_REACHED = "daily_limit_reached"


class Registration(Base):
    __tablename__ = "registrations"
    __table_args__ = (
        Index("ix_registrations_website_id", "website_id"),
        Index("ix_registrations_status", "status"),
        Index("ix_registrations_created_at", "created_at"),
        Index("ix_registrations_celery_task_id", "celery_task_id"),
        Index("ix_registrations_deleted_at", "deleted_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    website_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("websites.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[RegistrationStatus] = mapped_column(
        Enum(RegistrationStatus, name="registration_status"),
        default=RegistrationStatus.PENDING,
    )

    # Generated user data
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email_used: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    phone_used: Mapped[str | None] = mapped_column(String(50), nullable=True)
    password_used: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # OTP tracking
    email_otp_verified: Mapped[bool] = mapped_column(default=False)
    mobile_otp_verified: Mapped[bool] = mapped_column(default=False)

    # Task tracking
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    screenshot_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Proxy used for this registration
    proxy_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("proxies.id", ondelete="SET NULL"), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Soft delete
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    # ── relationships ──────────────────────────────────────
    website: Mapped[Website] = relationship(  # noqa: F821
        "Website", back_populates="registrations"
    )
    proxy: Mapped[Proxy | None] = relationship("Proxy", back_populates="registrations")  # noqa: F821
    rental_numbers: Mapped[list[RentalNumber]] = relationship(  # noqa: F821
        "RentalNumber", back_populates="registration", lazy="selectin"
    )
    task_logs: Mapped[list[TaskLog]] = relationship(  # noqa: F821
        "TaskLog", back_populates="registration", lazy="selectin"
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def __repr__(self) -> str:
        return f"<Registration(id={self.id}, status={self.status.value})>"
