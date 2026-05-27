"""Alembic async env.py for NTM — uses asyncpg with SQLAlchemy 2.0 async engine.

Every domain model must be imported here so autogenerate can see the full schema.
"""

import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ── Shared metadata ──────────────────────────────────────────────────────────
# Import every model module so their tables are registered on Base.metadata.
from backend.app.models.base import Base  # noqa: F401 — shared Base

# Core auth models
from backend.app.core.models import User, Tenant, Role, user_tenant_access  # noqa: F401

# Domain models
from backend.app.models.client import Client  # noqa: F401
from backend.app.models.mandate import Mandate  # noqa: F401
from backend.app.models.campaign import Campaign  # noqa: F401
from backend.app.models.campaign_concept import CampaignConcept  # noqa: F401
from backend.app.models.activation import Activation  # noqa: F401
from backend.app.models.budget import Budget  # noqa: F401
from backend.app.models.kpi import KPI  # noqa: F401
from backend.app.models.performance_metric import PerformanceMetric  # noqa: F401
from backend.app.models.report import Report  # noqa: F401
from backend.app.models.approval_log import ApprovalLog  # noqa: F401
from backend.app.models.audit_trail import AuditTrail  # noqa: F401
from backend.app.models.activation_platform_mapping import ActivationPlatformMapping  # noqa: F401
from backend.app.models.platform_config_template import PlatformConfigTemplate  # noqa: F401
from backend.app.models.physical_activation_log import PhysicalActivationLog  # noqa: F401
from backend.app.models.creative import GeneratedCreative  # noqa: F401
from backend.app.models.copy import GeneratedCopy  # noqa: F401
from backend.app.models.script import GeneratedScript  # noqa: F401
from backend.app.models.image import GeneratedImage  # noqa: F401
from backend.app.models.audio import GeneratedAudio  # noqa: F401
from backend.app.models.video import GeneratedVideo  # noqa: F401

# ── Alembic config ────────────────────────────────────────────────────────────

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url with DATABASE_URL env var if set
# (converts async driver to sync for Alembic's connection check)
database_url = os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url") or "")
# Alembic needs a sync-compatible URL for offline mode; async for online mode
config.set_main_option("sqlalchemy.url", database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generates SQL without DB connection)."""
    url = config.get_main_option("sqlalchemy.url")
    # Replace asyncpg with psycopg2 for offline SQL generation
    url = url.replace("+asyncpg", "+psycopg2") if "+asyncpg" in url else url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode using an async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online migration — wraps async runner."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
