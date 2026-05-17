"""Add users and audit_logs tables for security hardening

Revision ID: 003
Revises: 002
Create Date: 2026-05-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── enums ──────────────────────────────────────────────
    user_role = sa.Enum("viewer", "operator", "admin", "super_admin", name="user_role")
    user_role.create(op.get_bind(), checkfirst=True)

    audit_action = sa.Enum(
        "login_success",
        "login_failed",
        "logout",
        "token_refresh",
        "password_change",
        "access_denied",
        "permission_denied",
        "user_created",
        "user_updated",
        "user_deleted",
        "user_disabled",
        "role_changed",
        "secrets_accessed",
        "data_exported",
        "settings_changed",
        "website_created",
        "website_updated",
        "website_deleted",
        "rate_limit_exceeded",
        "suspicious_activity",
        name="audit_action",
    )
    audit_action.create(op.get_bind(), checkfirst=True)

    # ── users table ────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("username", sa.String(100), unique=True, nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", user_role, nullable=False, server_default="viewer"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])
    op.create_index("ix_users_is_active", "users", ["is_active"])

    # ── audit_logs table ───────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("user_email", sa.String(255), nullable=True),
        sa.Column("action", audit_action, nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=True),
        sa.Column("resource_id", sa.String(100), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_resource_type", "audit_logs", ["resource_type"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("users")
    sa.Enum(name="audit_action").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="user_role").drop(op.get_bind(), checkfirst=True)
