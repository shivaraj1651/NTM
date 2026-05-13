"""Create report table for AGT-15.

Revision ID: 2026_05_13_00
Revises: 2026_05_12_01
Create Date: 2026-05-13 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '2026_05_13_00'
down_revision = '2026_05_12_01'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create report table."""
    op.create_table(
        'report',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('mandate_id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('report_type', sa.String(10), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('report_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for query efficiency
    op.create_index(
        'ix_report_mandate_id',
        'report',
        ['mandate_id'],
        unique=False
    )
    op.create_index(
        'ix_report_tenant_id',
        'report',
        ['tenant_id'],
        unique=False
    )
    op.create_index(
        'ix_report_mandate_type_start',
        'report',
        ['mandate_id', 'report_type', 'period_start'],
        unique=False
    )
    op.create_index(
        'ix_report_tenant_type',
        'report',
        ['tenant_id', 'report_type'],
        unique=False
    )


def downgrade() -> None:
    """Drop report table."""
    op.drop_index('ix_report_tenant_type', table_name='report')
    op.drop_index('ix_report_mandate_type_start', table_name='report')
    op.drop_index('ix_report_tenant_id', table_name='report')
    op.drop_index('ix_report_mandate_id', table_name='report')
    op.drop_table('report')
