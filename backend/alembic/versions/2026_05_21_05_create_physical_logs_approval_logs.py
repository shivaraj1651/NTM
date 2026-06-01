"""Create physical_activation_logs and approval_logs tables.

Revision ID: 2026_05_21_05
Revises: 2026_05_21_04
Create Date: 2026-05-21 05:00:00.000000

"""
import sqlalchemy as sa

from alembic import op

revision = '2026_05_21_05'
down_revision = '2026_05_21_04'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'physical_activation_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('campaign_id', sa.String(), nullable=False),
        sa.Column('activation_id', sa.String(), nullable=True),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('channel', sa.String(), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('logged_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_pal_tenant', 'physical_activation_logs', ['tenant_id'])
    op.create_index('ix_pal_campaign', 'physical_activation_logs', ['campaign_id'])
    op.create_index('ix_pal_activation', 'physical_activation_logs', ['activation_id'])
    op.create_index('ix_pal_tenant_campaign', 'physical_activation_logs', ['tenant_id', 'campaign_id'])

    op.create_table(
        'approval_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('entity_type', sa.String(), nullable=False),
        sa.Column('entity_id', sa.String(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('actor_id', sa.String(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status_before', sa.String(), nullable=True),
        sa.Column('status_after', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_approval_logs_tenant', 'approval_logs', ['tenant_id'])
    op.create_index('ix_approval_logs_entity', 'approval_logs', ['entity_id'])
    op.create_index('ix_approval_logs_tenant_entity', 'approval_logs', ['tenant_id', 'entity_id'])


def downgrade() -> None:
    op.drop_index('ix_approval_logs_tenant_entity', 'approval_logs')
    op.drop_index('ix_approval_logs_entity', 'approval_logs')
    op.drop_index('ix_approval_logs_tenant', 'approval_logs')
    op.drop_table('approval_logs')
    op.drop_index('ix_pal_tenant_campaign', 'physical_activation_logs')
    op.drop_index('ix_pal_activation', 'physical_activation_logs')
    op.drop_index('ix_pal_campaign', 'physical_activation_logs')
    op.drop_index('ix_pal_tenant', 'physical_activation_logs')
    op.drop_table('physical_activation_logs')
