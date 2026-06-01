"""Create campaigns and campaign_concepts tables.

Revision ID: 2026_05_21_03
Revises: 2026_05_21_02
Create Date: 2026-05-21 03:00:00.000000

"""
import sqlalchemy as sa

from alembic import op

revision = '2026_05_21_03'
down_revision = '2026_05_21_02'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'campaigns',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('mandate_id', sa.String(), nullable=True),
        sa.Column('client_id', sa.String(), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_campaigns_tenant', 'campaigns', ['tenant_id'])
    op.create_index('ix_campaigns_mandate', 'campaigns', ['mandate_id'])
    op.create_index('ix_campaigns_client', 'campaigns', ['client_id'])

    op.create_table(
        'campaign_concepts',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('campaign_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('strategy', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('selected_by', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_campaign_concepts_tenant', 'campaign_concepts', ['tenant_id'])
    op.create_index('ix_campaign_concepts_campaign', 'campaign_concepts', ['campaign_id'])


def downgrade() -> None:
    op.drop_index('ix_campaign_concepts_campaign', 'campaign_concepts')
    op.drop_index('ix_campaign_concepts_tenant', 'campaign_concepts')
    op.drop_table('campaign_concepts')
    op.drop_index('ix_campaigns_client', 'campaigns')
    op.drop_index('ix_campaigns_mandate', 'campaigns')
    op.drop_index('ix_campaigns_tenant', 'campaigns')
    op.drop_table('campaigns')
