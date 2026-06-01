"""Create generated_creatives table for Creative Director Agent output.

Revision ID: 2026_05_09_00
Revises:
Create Date: 2026-05-09 00:00:00.000000

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = '2026_05_09_00'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create generated_creatives table with pgvector support."""
    op.create_table(
        'generated_creatives',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('campaign_id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('generation_id', sa.String(), nullable=False),
        sa.Column('platform', sa.String(), nullable=False),
        sa.Column('creative_type', sa.String(), nullable=False),
        sa.Column('content', postgresql.JSONB(), nullable=False),
        sa.Column('validation_status', sa.String(), nullable=False),
        sa.Column('refinement_attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index(
        'idx_generated_creatives_campaign_id',
        'generated_creatives',
        ['campaign_id'],
        unique=False
    )
    op.create_index(
        'idx_generated_creatives_tenant_id',
        'generated_creatives',
        ['tenant_id'],
        unique=False
    )
    op.create_index(
        'idx_generated_creatives_generation_id',
        'generated_creatives',
        ['generation_id'],
        unique=False
    )
    op.create_index(
        'idx_generated_creatives_platform',
        'generated_creatives',
        ['platform'],
        unique=False
    )

    # Create unique constraint on campaign_id, generation_id, platform, creative_type
    op.create_unique_constraint(
        'uq_generated_creatives_unique_creative',
        'generated_creatives',
        ['campaign_id', 'generation_id', 'platform', 'creative_type']
    )


def downgrade() -> None:
    """Drop generated_creatives table."""
    op.drop_table('generated_creatives')
