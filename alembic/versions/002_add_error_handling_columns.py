"""Add error handling & resilience columns to registrations

Revision ID: 002
Revises: 001
Create Date: 2026-05-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("registrations", sa.Column("html_snapshot_path", sa.Text(), nullable=True))
    op.add_column("registrations", sa.Column("browser_log_path", sa.Text(), nullable=True))
    op.add_column("registrations", sa.Column("error_category", sa.String(50), nullable=True))
    op.add_column("registrations", sa.Column("error_context", sa.JSON(), nullable=True))

    op.create_index("ix_registrations_error_category", "registrations", ["error_category"])


def downgrade() -> None:
    op.drop_index("ix_registrations_error_category", table_name="registrations")

    op.drop_column("registrations", "error_context")
    op.drop_column("registrations", "error_category")
    op.drop_column("registrations", "browser_log_path")
    op.drop_column("registrations", "html_snapshot_path")
