from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from configs.database import Base


class RegistrationStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    EMAIL_OTP_PENDING = "email_otp_pending"
    MOBILE_OTP_PENDING = "mobile_otp_pending"
    COMPLETED = "completed"
    FAILED = "failed"
    DAILY_LIMIT_REACHED = "daily_limit_reached"


class Registration(Base):
    __tablename__ = "registrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    website_id: Mapped[int] = mapped_column(Integer, ForeignKey("websites.id"), nullable=False)
    status: Mapped[RegistrationStatus] = mapped_column(
        Enum(RegistrationStatus), default=RegistrationStatus.PENDING
    )

    # Generated user data
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email_used: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone_used: Mapped[str | None] = mapped_column(String(50), nullable=True)
    password_used: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # OTP tracking
    email_otp_verified: Mapped[bool] = mapped_column(default=False)
    mobile_otp_verified: Mapped[bool] = mapped_column(default=False)

    # Task tracking
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    screenshot_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    website: Mapped[Website] = relationship("Website", back_populates="registrations")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Registration(id={self.id}, status={self.status})>"
