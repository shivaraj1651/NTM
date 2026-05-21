"""Create tenants, roles, user, user_tenant_access tables.

Revision ID: 2026_05_21_01
Revises: 2026_05_13_00
Create Date: 2026-05-21 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '2026_05_21_01'
down_revision = '2026_05_13_00'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'roles',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('permissions', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_roles_name', 'roles', ['name'], unique=True)

    op.create_table(
        'tenants',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_tenants_name', 'tenants', ['name'])

    op.create_table(
        'user',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('tenant_id', sa.String(), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('role_id', sa.String(), sa.ForeignKey('roles.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_email', 'user', ['email'], unique=True)
    op.create_index('ix_user_tenant_id', 'user', ['tenant_id'])

    op.create_table(
        'user_tenant_access',
        sa.Column('user_id', sa.String(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('tenant_id', sa.String(), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('user_id', 'tenant_id'),
    )


def downgrade() -> None:
    op.drop_table('user_tenant_access')
    op.drop_index('ix_user_tenant_id', 'user')
    op.drop_index('ix_user_email', 'user')
    op.drop_table('user')
    op.drop_index('ix_tenants_name', 'tenants')
    op.drop_table('tenants')
    op.drop_index('ix_roles_name', 'roles')
    op.drop_table('roles')
