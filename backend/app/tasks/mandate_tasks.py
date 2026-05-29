"""Celery task for AGT-01 mandate analysis."""

import asyncio
import logging
import os
from datetime import datetime, timezone

from celery import shared_task
from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, update

from backend.app.models.mandate import Mandate
from backend.app.agents.mandate_analyst import mandate_analyst_agent

logger = logging.getLogger(__name__)

MONGO_DB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGODB_DB", "ntm")


def _make_session_factory() -> async_sessionmaker:
    db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    engine = create_async_engine(db_url, echo=False)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

_SESSION_FACTORY: async_sessionmaker | None = None


def _get_session_factory() -> async_sessionmaker:
    global _SESSION_FACTORY
    if _SESSION_FACTORY is None:
        _SESSION_FACTORY = _make_session_factory()
    return _SESSION_FACTORY


async def _run_mandate_analysis(mandate_id: str, tenant_id: str) -> None:
    factory = _get_session_factory()

    async with factory() as session:
        result = await session.execute(
            select(Mandate).where(
                Mandate.id == mandate_id,
                Mandate.tenant_id == tenant_id,
            )
        )
        mandate = result.scalar_one_or_none()
        if not mandate:
            logger.error(f"[run_mandate_analysis] mandate not found: {mandate_id}")
            return

        mandate.status = "analyzing"
        await session.commit()
        mandate_dict = mandate.to_dict()

    # Run AGT-01 — exceptions propagate to Celery retry handler
    analysis = await mandate_analyst_agent(mandate_dict)

    mongo_client = AsyncIOMotorClient(MONGO_DB_URL)
    try:
        db = mongo_client[MONGO_DB_NAME]
        doc = {
            "mandate_id": mandate_id,
            "tenant_id": tenant_id,
            "analysis": analysis,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db["mandate_analyses"].insert_one(doc)
        logger.info(f"[run_mandate_analysis] Stored analysis for mandate {mandate_id}")
    finally:
        mongo_client.close()

    async with factory() as session:
        await session.execute(
            update(Mandate)
            .where(Mandate.id == mandate_id, Mandate.tenant_id == tenant_id)
            .values(status="analyzed")
        )
        await session.commit()

    # Auto-chain AGT-02: competitive intel pipeline runs after AGT-01 succeeds
    from backend.app.tasks.competitive_intel_tasks import run_competitive_intel_pipeline
    run_competitive_intel_pipeline.delay(mandate_id, tenant_id)
    logger.info(f"[run_mandate_analysis] dispatched CI pipeline for mandate {mandate_id}")


@shared_task(bind=True, max_retries=3)
def run_mandate_analysis(self, mandate_id: str, tenant_id: str) -> None:
    """Celery task: run AGT-01 mandate analysis and store output to MongoDB."""
    try:
        asyncio.run(_run_mandate_analysis(mandate_id, tenant_id))
    except Exception as e:
        logger.error(f"[run_mandate_analysis] task failed for {mandate_id}: {e}")
        raise self.retry(exc=e, countdown=2 ** self.request.retries)
