"""Celery tasks for campaign strategy pipeline (AGT-03)."""

import asyncio
import logging
import os
from datetime import datetime, timezone

from celery import shared_task
from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from sqlalchemy import select

from backend.app.models.mandate import Mandate
from backend.app.agents.campaign_strategist import campaign_strategist_agent

logger = logging.getLogger(__name__)

MONGO_DB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGODB_DB", "ntm")


def _make_session_factory() -> async_sessionmaker:
    db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    # NullPool + a fresh engine per call: Celery runs each task in its own
    # asyncio.run() loop, and a cached engine binds asyncpg connections to the
    # first loop ("another operation is in progress" on later tasks).
    engine = create_async_engine(db_url, echo=False, poolclass=NullPool)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def _get_session_factory() -> async_sessionmaker:
    # Do NOT cache — return a fresh factory bound to the current event loop.
    return _make_session_factory()


async def _run_campaign_strategy(mandate_id: str, tenant_id: str) -> None:
    """Async implementation: fetch mandate + CI report, run AGT-03, store output."""
    factory = _get_session_factory()

    # Fetch mandate from PostgreSQL
    async with factory() as session:
        result = await session.execute(
            select(Mandate).where(
                Mandate.id == mandate_id,
                Mandate.tenant_id == tenant_id,
            )
        )
        mandate = result.scalar_one_or_none()
        if not mandate:
            logger.error(f"[run_campaign_strategy] mandate not found: {mandate_id}")
            return
        mandate_dict = mandate.to_dict()

    # Fetch CI report from MongoDB (may be empty if competitive intel hasn't run)
    mongo_client = AsyncIOMotorClient(MONGO_DB_URL)
    try:
        db = mongo_client[MONGO_DB_NAME]
        ci_doc = await db["mandate_analyses"].find_one(
            {"mandate_id": mandate_id, "tenant_id": tenant_id}
        )
        ci_report = ci_doc.get("analysis", {}) if ci_doc else {}
    finally:
        mongo_client.close()

    # Run AGT-03 campaign strategist
    logger.info(f"[run_campaign_strategy] running AGT-03 for mandate_id={mandate_id}")
    output = await campaign_strategist_agent(mandate=mandate_dict, ci_report=ci_report)

    # Store concepts to MongoDB
    mongo_client = AsyncIOMotorClient(MONGO_DB_URL)
    try:
        db = mongo_client[MONGO_DB_NAME]
        await db["campaign_concepts"].update_one(
            {"mandate_id": mandate_id, "tenant_id": tenant_id},
            {"$set": {
                "mandate_id": mandate_id,
                "tenant_id": tenant_id,
                "concepts": output.get("campaigns", []),
                "validation_errors": output.get("validation_errors", []),
                "regeneration_log": output.get("regeneration_log", []),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }},
            upsert=True,
        )
        logger.info(f"[run_campaign_strategy] stored {len(output.get('campaigns', []))} concepts for mandate {mandate_id}")
    finally:
        mongo_client.close()


@shared_task(bind=True, max_retries=3)
def run_campaign_strategy(self, mandate_id: str, tenant_id: str) -> None:
    """Celery task: run AGT-03 campaign strategist for a confirmed mandate."""
    logger.info(f"[run_campaign_strategy] start mandate_id={mandate_id} tenant_id={tenant_id}")
    try:
        asyncio.run(_run_campaign_strategy(mandate_id, tenant_id))
        logger.info(f"[run_campaign_strategy] complete mandate_id={mandate_id}")
    except Exception as exc:
        logger.error(f"[run_campaign_strategy] error for {mandate_id}: {exc}")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


async def _run_media_planning(campaign_id: str, tenant_id: str) -> None:
    """Async implementation: fetch campaign concept, run AGT-04, store media plan."""
    from backend.app.agents.media_planner import media_planner_agent

    mongo_client = AsyncIOMotorClient(MONGO_DB_URL)
    try:
        db = mongo_client[MONGO_DB_NAME]
        campaign_doc = await db["campaigns"].find_one(
            {"_id": campaign_id, "tenant_id": tenant_id}
        )
        if not campaign_doc:
            logger.error(f"[run_media_planning] campaign not found: {campaign_id}")
            return

        concepts = campaign_doc.get("concepts", [])
        selected_concept_id = campaign_doc.get("selected_concept_id")
        if selected_concept_id:
            concept = next((c for c in concepts if c.get("id") == selected_concept_id), concepts[0] if concepts else {})
        else:
            concept = concepts[0] if concepts else {}

        budget_envelope = campaign_doc.get("budget_envelope", {
            "total_budget": campaign_doc.get("total_budget", 10000),
            "currency": "USD",
            "contingency_pct": 10,
        })
        mandate_geography = campaign_doc.get("geography", {"regions": [], "markets": [], "countries": []})

        logger.info(f"[run_media_planning] running AGT-04 for campaign_id={campaign_id}")
        output = await media_planner_agent(
            campaign_concept=concept,
            budget_envelope=budget_envelope,
            mandate_geography=mandate_geography,
            mandate_context=campaign_doc.get("mandate_context"),
        )

        await db["campaigns"].update_one(
            {"_id": campaign_id, "tenant_id": tenant_id},
            {"$set": {
                "activation_plan": output.get("activations", []),
                "budget_summary": output.get("budget_summary", {}),
                "media_plan_status": output.get("status", "generated"),
                "media_plan_generated_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
        logger.info(f"[run_media_planning] stored media plan for campaign {campaign_id}")
    finally:
        mongo_client.close()


@shared_task(bind=True, max_retries=3)
def run_media_planning(self, campaign_id: str, tenant_id: str) -> None:
    """Celery task: run AGT-04 media planner after campaign concept is confirmed."""
    logger.info(f"[run_media_planning] start campaign_id={campaign_id} tenant_id={tenant_id}")
    try:
        asyncio.run(_run_media_planning(campaign_id, tenant_id))
        logger.info(f"[run_media_planning] complete campaign_id={campaign_id}")
    except Exception as exc:
        logger.error(f"[run_media_planning] error for {campaign_id}: {exc}")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


async def _run_video_generation(campaign_id: str, tenant_id: str) -> None:
    """Async implementation: build brief from campaign creative assets, run AGT-11."""
    from backend.app.agents.video_generator import VideoGeneratorAgent, VideoGenerationBrief
    from backend.app.tools import runway as runway_tool

    mongo_client = AsyncIOMotorClient(MONGO_DB_URL)
    try:
        db = mongo_client[MONGO_DB_NAME]
        campaign_doc = await db["campaigns"].find_one(
            {"_id": campaign_id, "tenant_id": tenant_id}
        )
        if not campaign_doc:
            logger.error(f"[run_video_generation] campaign not found: {campaign_id}")
            return

        creative_assets = campaign_doc.get("creative_assets") or {}
        scripts = creative_assets.get("scripts") or []
        images = creative_assets.get("images") or []

        script_text = scripts[0].get("content", "") if scripts else ""
        reference_image_url = images[0].get("url") if images else None

        concept = (campaign_doc.get("concepts") or [{}])[0]
        prompt = (
            f"{concept.get('theme', '')} — {concept.get('narrative', '')} "
            f"Visual style: {concept.get('visual_direction', '')}".strip()
            or "Brand campaign social video"
        )

        brief = VideoGenerationBrief(
            campaign_id=campaign_id,
            tenant_id=tenant_id,
            prompt=prompt,
            script_text=script_text,
            reference_image_url=reference_image_url or None,
            duration_seconds=5,
            script_format="social_video",
            campaign_theme=concept.get("theme", ""),
        )

        agent = VideoGeneratorAgent()
        if not runway_tool.is_available():
            logger.warning(
                "[run_video_generation] RUNWAY_API_KEY not set — video asset will be "
                "marked manual_production_required"
            )

        output = await agent.generate(brief, storage_client=None, db_session=None)

        video_entry = {
            "id": output.generation_id,
            "format": "social_video",
            "url": output.asset_url,
            "job_id": output.job_id,
            "model_used": output.model_used,
            "duration_seconds": output.duration_seconds,
            "status": output.status,
            "approved": None,
            "revision_count": 0,
        }

        await db["campaigns"].update_one(
            {"_id": campaign_id, "tenant_id": tenant_id},
            {
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
                "$push": {"creative_assets.video": video_entry},
            },
        )
        logger.info(
            "[run_video_generation] complete campaign_id=%s status=%s",
            campaign_id, output.status,
        )
    finally:
        mongo_client.close()


@shared_task(bind=True, max_retries=2)
def run_video_generation(self, campaign_id: str, tenant_id: str) -> None:
    """Celery task: run AGT-11 video generator after creatives are generated."""
    logger.info(f"[run_video_generation] start campaign_id={campaign_id} tenant_id={tenant_id}")
    try:
        asyncio.run(_run_video_generation(campaign_id, tenant_id))
        logger.info(f"[run_video_generation] complete campaign_id={campaign_id}")
    except Exception as exc:
        logger.error(f"[run_video_generation] error for {campaign_id}: {exc}")
        raise self.retry(exc=exc, countdown=30)


async def _run_budget_optimization(campaign_id: str, tenant_id: str) -> None:
    """Async: fetch campaign doc, run AGT-05, store budget_proposal."""
    from backend.app.agents.budget_optimizer import budget_optimizer_agent

    mongo_client = AsyncIOMotorClient(MONGO_DB_URL)
    try:
        db = mongo_client[MONGO_DB_NAME]
        campaign_doc = await db["campaigns"].find_one({"_id": campaign_id, "tenant_id": tenant_id})
        if not campaign_doc:
            logger.error("[run_budget_optimization] campaign not found: %s", campaign_id)
            return

        activations = campaign_doc.get("activation_plan", []) or []
        mandate = await db["mandates"].find_one({"_id": campaign_doc.get("mandate_id"), "tenant_id": tenant_id}) or {}
        b = mandate.get("budget", {})
        budget_env = {"total_budget": b.get("total_amount", 0), "currency": b.get("currency", "USD")}
        concept = (campaign_doc.get("concepts") or [{}])[0]
        campaign_context = {
            "campaign_id": campaign_id,
            "campaign_name": concept.get("name", ""),
            "objective": mandate.get("objective", ""),
            "description": concept.get("narrative", ""),
            "target_audience": mandate.get("target_audience", ""),
            "tone_board": concept.get("tone_board", ""),
        }

        logger.info("[run_budget_optimization] running AGT-05 for campaign_id=%s", campaign_id)
        proposal = await budget_optimizer_agent(activations, budget_env, campaign_context)

        await db["campaigns"].find_one_and_update(
            {"_id": campaign_id, "tenant_id": tenant_id},
            {"$set": {
                "status": "budget_proposed",
                "budget_proposal": proposal if isinstance(proposal, dict) else proposal.model_dump(mode="json"),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
        logger.info("[run_budget_optimization] stored budget_proposal for campaign %s", campaign_id)
    finally:
        mongo_client.close()


@shared_task(bind=True, max_retries=3)
def run_budget_optimization(self, campaign_id: str, tenant_id: str) -> None:
    """Celery task: run AGT-05 budget optimizer after activation plan is ready."""
    logger.info("[run_budget_optimization] start campaign_id=%s tenant_id=%s", campaign_id, tenant_id)
    try:
        asyncio.run(_run_budget_optimization(campaign_id, tenant_id))
        logger.info("[run_budget_optimization] complete campaign_id=%s", campaign_id)
    except Exception as exc:
        logger.error("[run_budget_optimization] error for %s: %s", campaign_id, exc)
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
