"""add_cities_to_mandates

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-19

Adds optional cities JSON column to mandates table to store city-level
targeting alongside the existing countries field.
"""

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "mandates",
        sa.Column("cities", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("mandates", "cities")
