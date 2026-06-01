"""Create activations, activation_platform_mapping, and budgets tables.

Revision ID: 2026_05_21_04
Revises: 2026_05_21_03
Create Date: 2026-05-21 04:00:00.000000

"""
import sqlalchemy as sa

from alembic import op

revision = '2026_05_21_04'
down_revision = '2026_05_21_03'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'activations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('campaign_id', sa.String(), nullable=False),
        sa.Column('channel', sa.String(), nullable=False),
        sa.Column('sub_channel', sa.String(), nullable=True),
        sa.Column('audience_segment', sa.String(), nullable=False),
        sa.Column('budget_allocated', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(), nullable=False, server_default='USD'),
        sa.Column('platform_config', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='planned'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_activations_tenant', 'activations', ['tenant_id'])
    op.create_index('ix_activations_campaign', 'activations', ['campaign_id'])
    op.create_index('ix_activations_tenant_campaign', 'activations', ['tenant_id', 'campaign_id'])

    op.create_table(
        'activation_platform_mapping',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('activation_id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('channel_enum', sa.String(), nullable=False),
        sa.Column('platform_campaign_id', sa.String(), nullable=True),
        sa.Column('platform_ad_id', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'activation_id', 'channel_enum', 'tenant_id',
            name='uq_activation_platform_mapping_unique_channel',
        ),
    )
    op.create_index(
        'ix_activation_platform_mapping_tenant_activation',
        'activation_platform_mapping', ['tenant_id', 'activation_id'],
    )
    op.create_index(
        'ix_activation_platform_mapping_status',
        'activation_platform_mapping', ['status'],
    )
    op.create_index(
        'ix_activation_platform_mapping_channel',
        'activation_platform_mapping', ['channel_enum'],
    )

    op.create_table(
        'budgets',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('campaign_id', sa.String(), nullable=False),
        sa.Column('total', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(), nullable=False, server_default='USD'),
        sa.Column('breakdown', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='draft'),
        sa.Column('approved_by', sa.String(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_budgets_tenant', 'budgets', ['tenant_id'])
    op.create_index('ix_budgets_campaign', 'budgets', ['campaign_id'])


def downgrade() -> None:
    op.drop_index('ix_budgets_campaign', 'budgets')
    op.drop_index('ix_budgets_tenant', 'budgets')
    op.drop_table('budgets')
    op.drop_index('ix_activation_platform_mapping_channel', 'activation_platform_mapping')
    op.drop_index('ix_activation_platform_mapping_status', 'activation_platform_mapping')
    op.drop_index('ix_activation_platform_mapping_tenant_activation', 'activation_platform_mapping')
    op.drop_table('activation_platform_mapping')
    op.drop_index('ix_activations_tenant_campaign', 'activations')
    op.drop_index('ix_activations_campaign', 'activations')
    op.drop_index('ix_activations_tenant', 'activations')
    op.drop_table('activations')
