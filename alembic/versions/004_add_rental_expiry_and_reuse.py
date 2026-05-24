"""Add rental expiry and multi-OTP reuse support

Revision ID: 004
Revises: 003
Create Date: 2026-05-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "004"
down_revision: str = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add expires_at for 24hr rental tracking
    op.add_column(
        "rental_numbers",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Track how many OTPs have been received on this number
    op.add_column(
        "rental_numbers",
        sa.Column("otp_count", sa.Integer, server_default="0", nullable=False),
    )
    # Allow rental to exist without a specific registration (standalone rental)
    op.alter_column(
        "rental_numbers",
        "registration_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    # Add label to identify what this number was rented for
    op.add_column(
        "rental_numbers",
        sa.Column("label", sa.String(255), nullable=True),
    )
    # Index for finding active unexpired rentals by country
    op.create_index(
        "ix_rental_numbers_country_status_expires",
        "rental_numbers",
        ["country", "status", "expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_rental_numbers_country_status_expires", table_name="rental_numbers")
    op.drop_column("rental_numbers", "label")
    op.alter_column(
        "rental_numbers",
        "registration_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.drop_column("rental_numbers", "otp_count")
    op.drop_column("rental_numbers", "expires_at")
