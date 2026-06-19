"""Add cities column to mandates table.

Revision ID: 2026_06_19_01
Revises: 2026_05_21_05
Create Date: 2026-06-19 01:00:00.000000

"""
import sqlalchemy as sa

from alembic import op

revision = '2026_06_19_01'
down_revision = '2026_05_21_05'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'mandates',
        sa.Column('cities', sa.JSON(), nullable=True, server_default='[]'),
    )


def downgrade() -> None:
    op.drop_column('mandates', 'cities')
