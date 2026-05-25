"""Add sms-activate to rental_provider enum

Revision ID: 005
Revises: 004
Create Date: 2026-05-24
"""

from collections.abc import Sequence

from alembic import op

revision: str = "005"
down_revision: str = "004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE rental_provider ADD VALUE IF NOT EXISTS 'sms-activate'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values; no-op
    pass
