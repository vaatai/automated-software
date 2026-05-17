"""Audit logging — security events, admin actions, and access tracking.

Every security-relevant action (login, failed auth, permission denial,
data access, config change) is recorded in the ``audit_logs`` table
with actor identity, action, resource, and context.
"""

import enum
import json
import logging
from datetime import datetime

from sqlalchemy import DateTime, Enum, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from configs.database import Base

logger = logging.getLogger("security.audit")


class AuditAction(str, enum.Enum):
    """Categorised security events."""

    # Authentication
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    PASSWORD_CHANGE = "password_change"

    # Authorization
    ACCESS_DENIED = "access_denied"
    PERMISSION_DENIED = "permission_denied"

    # User management
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    USER_DISABLED = "user_disabled"
    ROLE_CHANGED = "role_changed"

    # Data access
    SECRETS_ACCESSED = "secrets_accessed"
    DATA_EXPORTED = "data_exported"

    # Configuration
    SETTINGS_CHANGED = "settings_changed"
    WEBSITE_CREATED = "website_created"
    WEBSITE_UPDATED = "website_updated"
    WEBSITE_DELETED = "website_deleted"

    # System
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"


class AuditLog(Base):
    """Immutable audit log record for security events."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_resource_type", "resource_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction, name="audit_action"), nullable=False
    )
    resource_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action.value}, user_id={self.user_id})>"


class AuditLogger:
    """Service for recording audit events.

    Writes to both the database and structured Python logging for
    integration with external SIEM/log aggregation systems.
    """

    def __init__(self, db_session=None) -> None:
        self._db = db_session

    async def log(
        self,
        action: AuditAction,
        *,
        user_id: int | None = None,
        user_email: str | None = None,
        resource_type: str | None = None,
        resource_id: str | int | None = None,
        details: dict | str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Record an audit event."""
        details_str = json.dumps(details, default=str) if isinstance(details, dict) else details

        # Always log to Python logger (structured)
        logger.info(
            "AUDIT: action=%s user_id=%s resource=%s/%s ip=%s",
            action.value,
            user_id,
            resource_type,
            resource_id,
            ip_address,
        )

        # Write to database if session available
        if self._db is not None:
            entry = AuditLog(
                user_id=user_id,
                user_email=user_email,
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id else None,
                details=details_str,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            self._db.add(entry)
            try:
                await self._db.flush()
            except Exception:
                logger.warning("Failed to write audit log to database")

    async def log_from_request(
        self,
        action: AuditAction,
        request,
        *,
        user=None,
        resource_type: str | None = None,
        resource_id: str | int | None = None,
        details: dict | str | None = None,
    ) -> None:
        """Record an audit event extracting IP and user agent from a FastAPI request."""
        ip = None
        if request:
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                ip = forwarded.split(",")[0].strip()
            elif request.client:
                ip = request.client.host

        await self.log(
            action,
            user_id=user.id if user else None,
            user_email=user.email if user else None,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip,
            user_agent=request.headers.get("User-Agent") if request else None,
        )
