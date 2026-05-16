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


class LogLevel(str, enum.Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class TaskLog(Base):
    """Granular event log for individual registration task execution."""

    __tablename__ = "task_logs"
    __table_args__ = (
        Index("ix_task_logs_registration_id", "registration_id"),
        Index("ix_task_logs_level", "level"),
        Index("ix_task_logs_created_at", "created_at"),
        Index("ix_task_logs_celery_task_id", "celery_task_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    registration_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("registrations.id", ondelete="CASCADE"), nullable=True
    )
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    level: Mapped[LogLevel] = mapped_column(
        Enum(LogLevel, name="log_level"), default=LogLevel.INFO
    )

    # Event details
    step: Mapped[str | None] = mapped_column(String(100), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    screenshot_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Duration tracking (ms)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── relationships ──────────────────────────────────────
    registration: Mapped[Registration | None] = relationship(  # noqa: F821
        "Registration", back_populates="task_logs"
    )

    def __repr__(self) -> str:
        return f"<TaskLog(id={self.id}, level={self.level.value}, step={self.step})>"
