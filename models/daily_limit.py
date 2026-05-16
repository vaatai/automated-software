from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from configs.database import Base


class DailyLimit(Base):
    __tablename__ = "daily_limits"
    __table_args__ = (
        UniqueConstraint("website_id", "date", name="uq_daily_limits_website_date"),
        Index("ix_daily_limits_website_id", "website_id"),
        Index("ix_daily_limits_date", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    website_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("websites.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    registration_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # ── relationships ──────────────────────────────────────
    website: Mapped[Website] = relationship("Website", back_populates="daily_limits")  # noqa: F821

    def __repr__(self) -> str:
        return f"<DailyLimit(website_id={self.website_id}, date={self.date}, count={self.registration_count})>"
