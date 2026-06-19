"""initial_schema

Revision ID: 0001
Revises:
Create Date: 2026-06-01

Full explicit DDL for every NTM table. Replaces the previous create_all()
stub so Alembic can track schema deltas going forward.

Existing databases: run `alembic stamp 0001` to mark them as already at
this revision without re-running the DDL.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── pgvector extension (no-op if already present) ─────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── roles ─────────────────────────────────────────────────────────────────
    op.create_table(
        "roles",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_roles_name", "roles", ["name"])

    # ── tenants ───────────────────────────────────────────────────────────────
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tenants_name", "tenants", ["name"])

    # ── user ──────────────────────────────────────────────────────────────────
    op.create_table(
        "user",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("role_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_user_email", "user", ["email"])
    op.create_index("ix_user_tenant_id", "user", ["tenant_id"])

    # ── user_tenant_access (junction) ─────────────────────────────────────────
    op.create_table(
        "user_tenant_access",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("user_id", "tenant_id"),
    )

    # ── clients ───────────────────────────────────────────────────────────────
    op.create_table(
        "clients",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("org_name", sa.String(), nullable=False),
        sa.Column("industry", sa.String(), nullable=False),
        sa.Column("logo_url", sa.String(), nullable=True),
        sa.Column("brand_guidelines_url", sa.String(), nullable=True),
        sa.Column("competitors", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clients_tenant", "clients", ["tenant_id"])

    # ── mandates ──────────────────────────────────────────────────────────────
    op.create_table(
        "mandates",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("client_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("objective", sa.String(), nullable=False),
        sa.Column("region", sa.String(), nullable=False),
        sa.Column("countries", sa.JSON(), nullable=False),
        sa.Column("competitors", sa.JSON(), nullable=False),
        sa.Column("total_budget", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mandates_tenant", "mandates", ["tenant_id"])
    op.create_index("ix_mandates_client", "mandates", ["client_id"])
    op.create_index("ix_mandates_tenant_client", "mandates", ["tenant_id", "client_id"])

    # ── campaigns ─────────────────────────────────────────────────────────────
    op.create_table(
        "campaigns",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("mandate_id", sa.String(), nullable=True),
        sa.Column("client_id", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_campaigns_tenant", "campaigns", ["tenant_id"])
    op.create_index("ix_campaigns_mandate", "campaigns", ["mandate_id"])
    op.create_index("ix_campaigns_client", "campaigns", ["client_id"])

    # ── campaign_concepts ─────────────────────────────────────────────────────
    op.create_table(
        "campaign_concepts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("campaign_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("strategy", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("selected_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_campaign_concepts_tenant", "campaign_concepts", ["tenant_id"])
    op.create_index("ix_campaign_concepts_campaign", "campaign_concepts", ["campaign_id"])

    # ── activations ───────────────────────────────────────────────────────────
    op.create_table(
        "activations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("campaign_id", sa.String(), nullable=False),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("sub_channel", sa.String(), nullable=True),
        sa.Column("audience_segment", sa.String(), nullable=False),
        sa.Column("budget_allocated", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(), nullable=False),
        sa.Column("platform_config", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_activations_tenant", "activations", ["tenant_id"])
    op.create_index("ix_activations_campaign", "activations", ["campaign_id"])
    op.create_index("ix_activations_tenant_campaign", "activations", ["tenant_id", "campaign_id"])

    # ── budgets ───────────────────────────────────────────────────────────────
    op.create_table(
        "budgets",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("campaign_id", sa.String(), nullable=False),
        sa.Column("total", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(), nullable=False),
        sa.Column("breakdown", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("approved_by", sa.String(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_budgets_tenant", "budgets", ["tenant_id"])
    op.create_index("ix_budgets_campaign", "budgets", ["campaign_id"])

    # ── kpi ───────────────────────────────────────────────────────────────────
    op.create_table(
        "kpi",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("campaign_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("channel_enum", sa.String(50), nullable=False),
        sa.Column("audience_segment", sa.String(100), nullable=False),
        sa.Column("kpi_name", sa.String(100), nullable=False),
        sa.Column("target_value", sa.Float(), nullable=False),
        sa.Column("threshold_unit", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "campaign_id", "channel_enum", "audience_segment", "kpi_name", "tenant_id",
            name="uq_kpi_campaign_channel_segment_name_tenant",
        ),
    )
    op.create_index("ix_kpi_campaign_id", "kpi", ["campaign_id"])
    op.create_index("ix_kpi_tenant_id", "kpi", ["tenant_id"])

    # ── performance_metric ────────────────────────────────────────────────────
    op.create_table(
        "performance_metric",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("activation_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("metrics_json", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_performance_metric_activation_id", "performance_metric", ["activation_id"])
    op.create_index("ix_performance_metric_tenant_id", "performance_metric", ["tenant_id"])
    op.create_index("ix_performance_metric_activation_date", "performance_metric", ["activation_id", "date"])
    op.create_index("ix_performance_metric_date_tenant", "performance_metric", ["date", "tenant_id"])

    # ── report ────────────────────────────────────────────────────────────────
    op.create_table(
        "report",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("mandate_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("report_type", sa.String(10), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("report_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_report_mandate_type_start", "report", ["mandate_id", "report_type", "period_start"])
    op.create_index("ix_report_tenant_type", "report", ["tenant_id", "report_type"])

    # ── approval_logs ─────────────────────────────────────────────────────────
    op.create_table(
        "approval_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("actor_id", sa.String(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status_before", sa.String(), nullable=True),
        sa.Column("status_after", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_logs_tenant", "approval_logs", ["tenant_id"])
    op.create_index("ix_approval_logs_entity", "approval_logs", ["entity_id"])
    op.create_index("ix_approval_logs_tenant_entity", "approval_logs", ["tenant_id", "entity_id"])

    # ── audit_trail ───────────────────────────────────────────────────────────
    op.create_table(
        "audit_trail",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("actor_id", sa.String(), nullable=False),
        sa.Column("actor_role", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("payload_before", sa.JSON(), nullable=True),
        sa.Column("payload_after", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_trail_tenant", "audit_trail", ["tenant_id"])
    op.create_index("ix_audit_trail_actor", "audit_trail", ["actor_id"])

    # ── activation_platform_mapping ───────────────────────────────────────────
    op.create_table(
        "activation_platform_mapping",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("activation_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("channel_enum", sa.String(), nullable=False),
        sa.Column("platform_campaign_id", sa.String(), nullable=True),
        sa.Column("platform_ad_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "activation_id", "channel_enum", "tenant_id",
            name="uq_activation_platform_mapping_unique_channel",
        ),
    )
    op.create_index("ix_activation_platform_mapping_activation_id", "activation_platform_mapping", ["activation_id"])
    op.create_index("ix_activation_platform_mapping_tenant_id", "activation_platform_mapping", ["tenant_id"])
    op.create_index("ix_activation_platform_mapping_tenant_activation", "activation_platform_mapping", ["tenant_id", "activation_id"])
    op.create_index("ix_activation_platform_mapping_status", "activation_platform_mapping", ["status"])
    op.create_index("ix_activation_platform_mapping_channel", "activation_platform_mapping", ["channel_enum"])

    # ── platform_config_template ──────────────────────────────────────────────
    op.create_table(
        "platform_config_template",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("channel_enum", sa.String(), nullable=False),
        sa.Column("audience_segment", sa.String(), nullable=False),
        sa.Column("platform_targeting_json", sa.JSON(), nullable=False),
        sa.Column("budget_multiplier", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "channel_enum", "audience_segment",
            name="uq_platform_config_template_unique",
        ),
    )
    op.create_index("ix_platform_config_template_tenant", "platform_config_template", ["tenant_id"])
    op.create_index("ix_platform_config_template_channel", "platform_config_template", ["channel_enum"])
    op.create_index("ix_platform_config_template_segment", "platform_config_template", ["audience_segment"])

    # ── physical_activation_logs ──────────────────────────────────────────────
    op.create_table(
        "physical_activation_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("campaign_id", sa.String(), nullable=False),
        sa.Column("activation_id", sa.String(), nullable=True),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("logged_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pal_tenant", "physical_activation_logs", ["tenant_id"])
    op.create_index("ix_pal_campaign", "physical_activation_logs", ["campaign_id"])
    op.create_index("ix_pal_activation", "physical_activation_logs", ["activation_id"])
    op.create_index("ix_pal_tenant_campaign", "physical_activation_logs", ["tenant_id", "campaign_id"])

    # ── generated_creatives ───────────────────────────────────────────────────
    op.create_table(
        "generated_creatives",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("campaign_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("generation_id", sa.String(), nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("creative_type", sa.String(), nullable=False),
        sa.Column("content", postgresql.JSONB(), nullable=False),
        sa.Column("validation_status", sa.String(), nullable=False),
        sa.Column("refinement_attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "campaign_id", "generation_id", "platform", "creative_type",
            name="uq_generated_creatives_unique_creative",
        ),
    )
    op.create_index("ix_generated_creatives_campaign_id", "generated_creatives", ["campaign_id"])
    op.create_index("ix_generated_creatives_tenant_id", "generated_creatives", ["tenant_id"])
    op.create_index("ix_generated_creatives_generation_id", "generated_creatives", ["generation_id"])
    op.create_index("ix_generated_creatives_platform", "generated_creatives", ["platform"])

    # ── generated_copy ────────────────────────────────────────────────────────
    op.create_table(
        "generated_copy",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("campaign_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("generation_id", sa.String(), nullable=False),
        sa.Column("asset_type", sa.String(), nullable=False),
        sa.Column("variant_id", sa.String(), nullable=False),
        sa.Column("content", postgresql.JSONB(), nullable=False),
        sa.Column("word_count", sa.Integer(), nullable=False),
        sa.Column("model_used", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "campaign_id", "generation_id", "asset_type", "variant_id",
            name="uq_generated_copy_unique_variant",
        ),
    )
    op.create_index("ix_generated_copy_campaign_id", "generated_copy", ["campaign_id"])
    op.create_index("ix_generated_copy_tenant_id", "generated_copy", ["tenant_id"])
    op.create_index("ix_generated_copy_generation_id", "generated_copy", ["generation_id"])
    op.create_index("ix_generated_copy_tenant_campaign", "generated_copy", ["tenant_id", "campaign_id"])

    # ── generated_scripts ─────────────────────────────────────────────────────
    op.create_table(
        "generated_scripts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("campaign_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("generation_id", sa.String(), nullable=False),
        sa.Column("script_format", sa.String(), nullable=False),
        sa.Column("variant_label", sa.String(), nullable=False),
        sa.Column("content", postgresql.JSONB(), nullable=False),
        sa.Column("production_brief", sa.Text(), nullable=False),
        sa.Column("model_used", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "campaign_id", "generation_id", "script_format", "variant_label",
            name="uq_generated_script_unique_variant",
        ),
    )
    op.create_index("ix_generated_scripts_campaign_id", "generated_scripts", ["campaign_id"])
    op.create_index("ix_generated_scripts_tenant_id", "generated_scripts", ["tenant_id"])
    op.create_index("ix_generated_scripts_generation_id", "generated_scripts", ["generation_id"])
    op.create_index("ix_generated_script_tenant_campaign", "generated_scripts", ["tenant_id", "campaign_id"])

    # ── generated_images ──────────────────────────────────────────────────────
    op.create_table(
        "generated_images",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("campaign_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("generation_id", sa.String(), nullable=False),
        sa.Column("asset_url", sa.String(), nullable=False),
        sa.Column("prompt_used", sa.Text(), nullable=False),
        sa.Column("model_used", sa.String(), nullable=False),
        sa.Column("generation_params", postgresql.JSONB(), nullable=False),
        sa.Column("image_format", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_generated_images_campaign_id", "generated_images", ["campaign_id"])
    op.create_index("ix_generated_images_tenant_id", "generated_images", ["tenant_id"])
    op.create_index("ix_generated_image_tenant_campaign", "generated_images", ["tenant_id", "campaign_id"])

    # ── generated_audio ───────────────────────────────────────────────────────
    op.create_table(
        "generated_audio",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("campaign_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("generation_id", sa.String(), nullable=False),
        sa.Column("asset_url", sa.String(), nullable=False),
        sa.Column("voice_id", sa.String(), nullable=False),
        sa.Column("model_used", sa.String(), nullable=False),
        sa.Column("script_format", sa.String(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_generated_audio_campaign_id", "generated_audio", ["campaign_id"])
    op.create_index("ix_generated_audio_tenant_id", "generated_audio", ["tenant_id"])
    op.create_index("ix_generated_audio_tenant_campaign", "generated_audio", ["tenant_id", "campaign_id"])

    # ── generated_video ───────────────────────────────────────────────────────
    op.create_table(
        "generated_video",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("campaign_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("generation_id", sa.String(), nullable=False),
        sa.Column("asset_url", sa.String(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("model_used", sa.String(), nullable=False),
        sa.Column("script_format", sa.String(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_generated_video_campaign_id", "generated_video", ["campaign_id"])
    op.create_index("ix_generated_video_tenant_id", "generated_video", ["tenant_id"])
    op.create_index("ix_generated_video_tenant_campaign", "generated_video", ["tenant_id", "campaign_id"])


def downgrade() -> None:
    op.drop_table("generated_video")
    op.drop_table("generated_audio")
    op.drop_table("generated_images")
    op.drop_table("generated_scripts")
    op.drop_table("generated_copy")
    op.drop_table("generated_creatives")
    op.drop_table("physical_activation_logs")
    op.drop_table("platform_config_template")
    op.drop_table("activation_platform_mapping")
    op.drop_table("audit_trail")
    op.drop_table("approval_logs")
    op.drop_table("report")
    op.drop_table("performance_metric")
    op.drop_table("kpi")
    op.drop_table("budgets")
    op.drop_table("activations")
    op.drop_table("campaign_concepts")
    op.drop_table("campaigns")
    op.drop_table("mandates")
    op.drop_table("clients")
    op.drop_table("user_tenant_access")
    op.drop_table("user")
    op.drop_table("tenants")
    op.drop_table("roles")
    op.execute("DROP EXTENSION IF EXISTS vector")
