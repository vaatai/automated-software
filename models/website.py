from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from configs.database import Base


class WebsiteStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class Website(Base):
    __tablename__ = "websites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[WebsiteStatus] = mapped_column(
        Enum(WebsiteStatus), default=WebsiteStatus.ACTIVE
    )

    # Form field selectors (CSS / XPath) stored as JSON
    form_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # OTP settings
    requires_email_otp: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_mobile_otp: Mapped[bool] = mapped_column(Boolean, default=False)

    # Rate limiting
    max_registrations_per_day: Mapped[int] = mapped_column(Integer, default=100)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    registrations: Mapped[list[Registration]] = relationship(  # noqa: F821
        "Registration", back_populates="website", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Website(id={self.id}, name={self.name})>"
