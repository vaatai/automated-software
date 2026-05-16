from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
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


class ProxyProtocol(str, enum.Enum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"


class ProxyStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    RATE_LIMITED = "rate_limited"
    BANNED = "banned"


class Proxy(Base):
    """Proxy pool for rotating IPs during registration."""

    __tablename__ = "proxies"
    __table_args__ = (
        Index("ix_proxies_status", "status"),
        Index("ix_proxies_protocol", "protocol"),
        Index("ix_proxies_deleted_at", "deleted_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    protocol: Mapped[ProxyProtocol] = mapped_column(
        Enum(ProxyProtocol, name="proxy_protocol"), default=ProxyProtocol.HTTP
    )
    status: Mapped[ProxyStatus] = mapped_column(
        Enum(ProxyStatus, name="proxy_status"), default=ProxyStatus.ACTIVE
    )

    # Authentication (optional)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Metadata
    country: Mapped[str | None] = mapped_column(String(10), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Health tracking
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fail_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_response_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Notes
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
        "Registration", back_populates="proxy", lazy="selectin"
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @property
    def url(self) -> str:
        auth = f"{self.username}:{self.password}@" if self.username else ""
        return f"{self.protocol.value}://{auth}{self.host}:{self.port}"

    def __repr__(self) -> str:
        return f"<Proxy(id={self.id}, host={self.host}:{self.port}, status={self.status.value})>"
