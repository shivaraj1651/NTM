"""Create clients and mandates tables.

Revision ID: 2026_05_21_02
Revises: 2026_05_21_01
Create Date: 2026-05-21 02:00:00.000000

"""
import sqlalchemy as sa

from alembic import op

revision = '2026_05_21_02'
down_revision = '2026_05_21_01'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'clients',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('org_name', sa.String(), nullable=False),
        sa.Column('industry', sa.String(), nullable=False),
        sa.Column('logo_url', sa.String(), nullable=True),
        sa.Column('brand_guidelines_url', sa.String(), nullable=True),
        sa.Column('competitors', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_clients_tenant', 'clients', ['tenant_id'])

    op.create_table(
        'mandates',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('client_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('objective', sa.String(), nullable=False),
        sa.Column('region', sa.String(), nullable=False),
        sa.Column('countries', sa.JSON(), nullable=False),
        sa.Column('competitors', sa.JSON(), nullable=False),
        sa.Column('total_budget', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(), nullable=False, server_default='USD'),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_mandates_tenant', 'mandates', ['tenant_id'])
    op.create_index('ix_mandates_client', 'mandates', ['client_id'])
    op.create_index('ix_mandates_tenant_client', 'mandates', ['tenant_id', 'client_id'])


def downgrade() -> None:
    op.drop_index('ix_mandates_tenant_client', 'mandates')
    op.drop_index('ix_mandates_client', 'mandates')
    op.drop_index('ix_mandates_tenant', 'mandates')
    op.drop_table('mandates')
    op.drop_index('ix_clients_tenant', 'clients')
    op.drop_table('clients')
