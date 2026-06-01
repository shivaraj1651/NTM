"""Create KPI table for analytics.

Revision ID: 2026_05_12_00
Revises: 2026_05_09_00
Create Date: 2026-05-12 00:00:00.000000

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = '2026_05_12_00'
down_revision = '2026_05_09_00'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create KPI table."""
    op.create_table(
        'kpi',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('campaign_id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('channel_enum', sa.String(50), nullable=False),
        sa.Column('audience_segment', sa.String(100), nullable=False),
        sa.Column('kpi_name', sa.String(100), nullable=False),
        sa.Column('target_value', sa.Float(), nullable=False),
        sa.Column('threshold_unit', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index(
        'ix_kpi_campaign_id',
        'kpi',
        ['campaign_id'],
        unique=False
    )
    op.create_index(
        'ix_kpi_tenant_id',
        'kpi',
        ['tenant_id'],
        unique=False
    )

    # Create unique constraint
    op.create_unique_constraint(
        'uq_kpi_campaign_channel_segment_name_tenant',
        'kpi',
        ['campaign_id', 'channel_enum', 'audience_segment', 'kpi_name', 'tenant_id']
    )


def downgrade() -> None:
    """Drop KPI table."""
    op.drop_table('kpi')
