"""Create PerformanceMetric table for analytics.

Revision ID: 2026_05_12_01
Revises: 2026_05_12_00
Create Date: 2026-05-12 01:00:00.000000

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = '2026_05_12_01'
down_revision = '2026_05_12_00'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create PerformanceMetric table."""
    op.create_table(
        'performance_metric',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('activation_id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('metrics_json', sa.JSON(), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for query efficiency
    op.create_index(
        'ix_performance_metric_activation_date',
        'performance_metric',
        ['activation_id', 'date'],
        unique=False
    )
    op.create_index(
        'ix_performance_metric_date_tenant',
        'performance_metric',
        ['date', 'tenant_id'],
        unique=False
    )
    op.create_index(
        'ix_performance_metric_activation_id',
        'performance_metric',
        ['activation_id'],
        unique=False
    )
    op.create_index(
        'ix_performance_metric_tenant_id',
        'performance_metric',
        ['tenant_id'],
        unique=False
    )


def downgrade() -> None:
    """Drop PerformanceMetric table."""
    op.drop_table('performance_metric')
