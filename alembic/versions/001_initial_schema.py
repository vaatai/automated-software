"""Initial schema — all 7 tables

Revision ID: 001
Revises:
Create Date: 2026-05-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── enums ──────────────────────────────────────────────
    website_status = sa.Enum("active", "inactive", "paused", "error", name="website_status")
    registration_status = sa.Enum(
        "pending", "in_progress", "email_otp_pending", "mobile_otp_pending",
        "completed", "failed", "cancelled", "daily_limit_reached",
        name="registration_status",
    )
    otp_provider = sa.Enum("mailslurp", "5sim", "pvapins", name="otp_provider")
    otp_type = sa.Enum("email", "sms", name="otp_type")
    rental_provider = sa.Enum("5sim", "pvapins", name="rental_provider")
    rental_status = sa.Enum(
        "rented", "otp_received", "finished", "cancelled", "expired",
        name="rental_status",
    )
    proxy_protocol = sa.Enum("http", "https", "socks5", name="proxy_protocol")
    proxy_status = sa.Enum("active", "inactive", "rate_limited", "banned", name="proxy_status")
    log_level = sa.Enum("debug", "info", "warning", "error", "critical", name="log_level")

    website_status.create(op.get_bind(), checkfirst=True)
    registration_status.create(op.get_bind(), checkfirst=True)
    otp_provider.create(op.get_bind(), checkfirst=True)
    otp_type.create(op.get_bind(), checkfirst=True)
    rental_provider.create(op.get_bind(), checkfirst=True)
    rental_status.create(op.get_bind(), checkfirst=True)
    proxy_protocol.create(op.get_bind(), checkfirst=True)
    proxy_status.create(op.get_bind(), checkfirst=True)
    log_level.create(op.get_bind(), checkfirst=True)

    # ── 1. websites ────────────────────────────────────────
    op.create_table(
        "websites",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("status", website_status, server_default="active"),
        sa.Column("form_config", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("requires_email_otp", sa.Boolean, server_default="false"),
        sa.Column("requires_mobile_otp", sa.Boolean, server_default="false"),
        sa.Column("registration_only_mode", sa.Boolean, server_default="false"),
        sa.Column("max_registrations_per_day", sa.Integer, server_default="100"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_websites_name", "websites", ["name"])
    op.create_index("ix_websites_status", "websites", ["status"])
    op.create_index("ix_websites_deleted_at", "websites", ["deleted_at"])

    # ── 2. proxies ─────────────────────────────────────────
    op.create_table(
        "proxies",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("host", sa.String(255), nullable=False),
        sa.Column("port", sa.Integer, nullable=False),
        sa.Column("protocol", proxy_protocol, server_default="http"),
        sa.Column("status", proxy_status, server_default="active"),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("password", sa.String(255), nullable=True),
        sa.Column("country", sa.String(10), nullable=True),
        sa.Column("provider", sa.String(100), nullable=True),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fail_count", sa.Integer, server_default="0"),
        sa.Column("success_count", sa.Integer, server_default="0"),
        sa.Column("avg_response_ms", sa.Integer, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_proxies_status", "proxies", ["status"])
    op.create_index("ix_proxies_protocol", "proxies", ["protocol"])
    op.create_index("ix_proxies_deleted_at", "proxies", ["deleted_at"])

    # ── 3. registrations ───────────────────────────────────
    op.create_table(
        "registrations",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("website_id", sa.Integer, sa.ForeignKey("websites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", registration_status, server_default="pending"),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("email_used", sa.String(255), nullable=True),
        sa.Column("phone_used", sa.String(50), nullable=True),
        sa.Column("password_used", sa.String(255), nullable=True),
        sa.Column("email_otp_verified", sa.Boolean, server_default="false"),
        sa.Column("mobile_otp_verified", sa.Boolean, server_default="false"),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("retry_count", sa.Integer, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("screenshot_path", sa.Text, nullable=True),
        sa.Column("proxy_id", sa.Integer, sa.ForeignKey("proxies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_registrations_website_id", "registrations", ["website_id"])
    op.create_index("ix_registrations_status", "registrations", ["status"])
    op.create_index("ix_registrations_created_at", "registrations", ["created_at"])
    op.create_index("ix_registrations_celery_task_id", "registrations", ["celery_task_id"])
    op.create_index("ix_registrations_email_used", "registrations", ["email_used"])
    op.create_index("ix_registrations_deleted_at", "registrations", ["deleted_at"])

    # ── 4. otp_configs ─────────────────────────────────────
    op.create_table(
        "otp_configs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("website_id", sa.Integer, sa.ForeignKey("websites.id", ondelete="CASCADE"), nullable=True),
        sa.Column("provider", otp_provider, nullable=False),
        sa.Column("otp_type", otp_type, nullable=False),
        sa.Column("api_key", sa.Text, nullable=False),
        sa.Column("base_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("priority", sa.Integer, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_otp_configs_provider_type", "otp_configs", ["provider", "otp_type"])
    op.create_index("ix_otp_configs_website_id", "otp_configs", ["website_id"])
    op.create_index("ix_otp_configs_deleted_at", "otp_configs", ["deleted_at"])

    # ── 5. daily_limits ────────────────────────────────────
    op.create_table(
        "daily_limits",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("website_id", sa.Integer, sa.ForeignKey("websites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("registration_count", sa.Integer, server_default="0"),
        sa.Column("success_count", sa.Integer, server_default="0"),
        sa.Column("failure_count", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_daily_limits_website_id", "daily_limits", ["website_id"])
    op.create_index("ix_daily_limits_date", "daily_limits", ["date"])
    op.create_unique_constraint("uq_daily_limits_website_date", "daily_limits", ["website_id", "date"])

    # ── 6. rental_numbers ──────────────────────────────────
    op.create_table(
        "rental_numbers",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("registration_id", sa.Integer, sa.ForeignKey("registrations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", rental_provider, nullable=False),
        sa.Column("status", rental_status, server_default="rented"),
        sa.Column("order_id", sa.String(255), nullable=False),
        sa.Column("phone_number", sa.String(50), nullable=False),
        sa.Column("country", sa.String(10), nullable=True),
        sa.Column("otp_code", sa.String(20), nullable=True),
        sa.Column("raw_sms", sa.Text, nullable=True),
        sa.Column("cost", sa.Float, nullable=True),
        sa.Column("currency", sa.String(10), nullable=True),
        sa.Column("rented_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("otp_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_rental_numbers_registration_id", "rental_numbers", ["registration_id"])
    op.create_index("ix_rental_numbers_provider", "rental_numbers", ["provider"])
    op.create_index("ix_rental_numbers_status", "rental_numbers", ["status"])
    op.create_index("ix_rental_numbers_phone_number", "rental_numbers", ["phone_number"])
    op.create_index("ix_rental_numbers_order_id", "rental_numbers", ["order_id"])
    op.create_index("ix_rental_numbers_deleted_at", "rental_numbers", ["deleted_at"])

    # ── 7. task_logs ───────────────────────────────────────
    op.create_table(
        "task_logs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("registration_id", sa.Integer, sa.ForeignKey("registrations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("level", log_level, server_default="info"),
        sa.Column("step", sa.String(100), nullable=True),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("details", sa.Text, nullable=True),
        sa.Column("screenshot_path", sa.Text, nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_task_logs_registration_id", "task_logs", ["registration_id"])
    op.create_index("ix_task_logs_level", "task_logs", ["level"])
    op.create_index("ix_task_logs_created_at", "task_logs", ["created_at"])
    op.create_index("ix_task_logs_celery_task_id", "task_logs", ["celery_task_id"])


def downgrade() -> None:
    op.drop_table("task_logs")
    op.drop_table("rental_numbers")
    op.drop_table("daily_limits")
    op.drop_table("otp_configs")
    op.drop_table("registrations")
    op.drop_table("proxies")
    op.drop_table("websites")

    for enum_name in [
        "log_level", "proxy_status", "proxy_protocol", "rental_status",
        "rental_provider", "otp_type", "otp_provider", "registration_status",
        "website_status",
    ]:
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
