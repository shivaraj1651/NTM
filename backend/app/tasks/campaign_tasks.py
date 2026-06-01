"""Celery tasks for campaign strategy pipeline (AGT-03)."""

import asyncio
import logging
import os
from datetime import datetime, timezone
from uuid import uuid4

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


async def _run_concept_generation(campaign_id: str, tenant_id: str) -> None:
    """Async: fetch campaign doc + mandate + CI report, run AGT-03, store concepts."""
    mongo_client = AsyncIOMotorClient(MONGO_DB_URL)
    try:
        db = mongo_client[MONGO_DB_NAME]
        campaign_doc = await db["campaigns"].find_one({"_id": campaign_id, "tenant_id": tenant_id})
        if not campaign_doc:
            logger.error("[run_concept_generation] campaign not found: %s", campaign_id)
            return

        mandate_id = campaign_doc.get("mandate_id")

        # Try Mongo mandates first, then mandate_analyses for CI report
        mandate = await db["mandates"].find_one({"_id": mandate_id, "tenant_id": tenant_id}) or {}
        ci_doc = await db["mandate_analyses"].find_one({"mandate_id": mandate_id, "tenant_id": tenant_id})
        ci_report = ci_doc.get("analysis", {}) if ci_doc else {}

        mandate_dict = {k: v for k, v in mandate.items() if k != "_id"} if mandate else {}

        logger.info("[run_concept_generation] running AGT-03 for campaign_id=%s", campaign_id)
        output = await campaign_strategist_agent(mandate=mandate_dict, ci_report=ci_report)

        val_errs = output.get("validation_errors", [])
        regen_log = output.get("regeneration_log", [])
        if val_errs:
            logger.warning("[run_concept_generation] %d concepts dropped by validation for %s: %s",
                           len(val_errs), campaign_id, val_errs)
        if regen_log:
            logger.info("[run_concept_generation] regen log for %s: %s", campaign_id, regen_log)

        import uuid as _uuid
        # Real LLM output doesn't include an id field — assign stable UUIDs now so
        # confirm's concept-id lookup always resolves.
        concepts = output.get("campaigns", [])
        for c in concepts:
            if not c.get("id"):
                c["id"] = str(_uuid.uuid4())

        await db["campaigns"].find_one_and_update(
            {"_id": campaign_id, "tenant_id": tenant_id},
            {"$set": {
                "status": "concepts_ready",
                "concepts": concepts,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
        logger.info("[run_concept_generation] stored %d concepts for campaign %s", len(concepts), campaign_id)
    except Exception as exc:
        logger.error("[run_concept_generation] error for %s: %s", campaign_id, exc)
        try:
            mongo_client2 = AsyncIOMotorClient(MONGO_DB_URL)
            try:
                db2 = mongo_client2[MONGO_DB_NAME]
                await db2["campaigns"].find_one_and_update(
                    {"_id": campaign_id, "tenant_id": tenant_id},
                    {"$set": {
                        "error": f"concept generation failed: {exc}",
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }},
                )
            finally:
                mongo_client2.close()
        except Exception:
            pass
        raise
    finally:
        mongo_client.close()


@shared_task(bind=True, max_retries=2)
def run_concept_generation(self, campaign_id: str, tenant_id: str) -> None:
    """Celery task: run AGT-03 campaign strategist for a new campaign (background)."""
    logger.info("[run_concept_generation] start campaign_id=%s tenant_id=%s", campaign_id, tenant_id)
    try:
        asyncio.run(_run_concept_generation(campaign_id, tenant_id))
        logger.info("[run_concept_generation] complete campaign_id=%s", campaign_id)
    except Exception as exc:
        logger.error("[run_concept_generation] error for %s: %s", campaign_id, exc)
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

        # Load the mandate for budget and geography — the campaign doc itself does not
        # carry these; they live on the mandate (Mongo mirror or Postgres-flat shape).
        mandate_doc = await db["mandates"].find_one(
            {"_id": campaign_doc.get("mandate_id"), "tenant_id": tenant_id}
        ) or {}

        # Budget: support both nested {budget:{total_amount,currency}} and flat {total_budget,currency}
        _b = mandate_doc.get("budget") or {}
        budget_envelope = {
            "total_budget": _b.get("total_amount") or mandate_doc.get("total_budget") or 10000,
            "currency":     _b.get("currency")     or mandate_doc.get("currency")     or "USD",
            "contingency_pct": 0.10,
        }

        # Geography: support {country_list:[...]} (Mongo mirror) and {countries:[...]} (flat Postgres)
        countries = (mandate_doc.get("country_list") or
                     mandate_doc.get("countries") or
                     mandate_doc.get("geography", {}).get("country_list") or
                     mandate_doc.get("geography", {}).get("markets") or [])
        mandate_geography = {
            "regions":      mandate_doc.get("geography", {}).get("regions") or
                            ([mandate_doc["region"]] if mandate_doc.get("region") else []),
            "country_list": countries,
            "markets":      countries,   # media_planner reads 'markets' key
            "countries":    countries,
        }

        # Mandate context for the LLM intelligence layer
        mandate_context = {
            "objective":       mandate_doc.get("objective", ""),
            "description":     mandate_doc.get("description", "") or mandate_doc.get("name", ""),
            "target_audience": mandate_doc.get("target_audience", "general consumers"),
        }

        logger.info(f"[run_media_planning] running AGT-04 for campaign_id={campaign_id} "
                    f"budget={budget_envelope['total_budget']} countries={countries}")
        output = await media_planner_agent(
            campaign_concept=concept,
            budget_envelope=budget_envelope,
            mandate_geography=mandate_geography,
            mandate_context=mandate_context,
        )

        # Serialize Pydantic Activation models → plain dicts for Motor/BSON
        raw_activations = output.get("activations", [])
        activations_serialized = [
            a.model_dump(mode="json") if hasattr(a, "model_dump")
            else (a.dict() if hasattr(a, "dict") else dict(a))
            for a in raw_activations
        ]
        await db["campaigns"].update_one(
            {"_id": campaign_id, "tenant_id": tenant_id},
            {"$set": {
                "status": "planned",
                "activation_plan": activations_serialized,
                "budget_summary": output.get("budget_summary", {}),
                "media_plan_status": output.get("status", "generated"),
                "media_plan_generated_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
        logger.info(f"[run_media_planning] stored %d activations for campaign %s",
                    len(activations_serialized), campaign_id)
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
        b = mandate.get("budget") or {"total_amount": mandate.get("total_budget", 0), "currency": mandate.get("currency", "USD")}
        budget_env = {"total_budget": b.get("total_amount", b.get("total_budget", 0)), "currency": b.get("currency", "USD")}
        concept = (campaign_doc.get("concepts") or [{}])[0]
        campaign_context = {
            "campaign_id": campaign_id,
            "campaign_name": concept.get("name", ""),
            "objective": mandate.get("objective", ""),
            "description": concept.get("narrative", ""),
            "target_audience": mandate.get("target_audience", ""),
            "tone_board": concept.get("tone_board", ""),
        }

        logger.info("[run_budget_optimization] running AGT-05 for campaign_id=%s activations=%d",
                    campaign_id, len(activations))
        proposal = await budget_optimizer_agent(activations, budget_env, campaign_context)

        # The optimizer returns {optimized_activations, roi_analysis, optimization_report, ...}.
        # The frontend BudgetPage reads {total_budget, currency, allocations[{channel,amount,percentage}]}.
        # Derive that shape from the optimizer's output so the UI renders correctly.
        source_acts = proposal.get("optimized_activations") or activations or []
        channel_totals: dict = {}
        for act in source_acts:
            ch = act.get("sub_channel") or act.get("channel_enum") or "Other"
            cost = float(act.get("optimized_cost_estimated") or act.get("cost_estimated") or 0)
            channel_totals[ch] = channel_totals.get(ch, 0.0) + cost

        total_bgt = float(budget_env.get("total_budget") or 0)
        actual_total = sum(channel_totals.values()) or total_bgt or 1.0
        currency_code = budget_env.get("currency", "USD")
        exec_summary = (proposal.get("optimization_report") or {}).get(
            "executive_summary", ""
        )

        budget_proposal_doc = {
            "total_budget": round(actual_total, 2),
            "currency": currency_code,
            "allocations": [
                {
                    "channel": ch,
                    "amount": round(amt, 2),
                    "percentage": round(amt / actual_total * 100, 1) if actual_total else 0,
                }
                for ch, amt in sorted(channel_totals.items(), key=lambda x: -x[1])
            ],
            "executive_summary": exec_summary,
        }

        await db["campaigns"].find_one_and_update(
            {"_id": campaign_id, "tenant_id": tenant_id},
            {"$set": {
                "status": "budget_proposed",
                "budget_proposal": budget_proposal_doc,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
        logger.info("[run_budget_optimization] stored budget_proposal for campaign %s "
                    "total=%.0f %s allocations=%d",
                    campaign_id, actual_total, currency_code, len(budget_proposal_doc["allocations"]))
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


# ---------------------------------------------------------------------------
# Creative generation: AGT-07 (Copywriter) + AGT-08 (Scriptwriter)
# ---------------------------------------------------------------------------

class _MinioStorageClient:
    """Upload bytes to MinIO and return a browser-accessible public URL."""

    def __init__(self) -> None:
        import boto3, json
        self._bucket = os.getenv("S3_BUCKET", "ntm-assets")
        endpoint = os.getenv("S3_ENDPOINT_URL", "http://localhost:9000")
        public_ep = os.getenv("S3_PUBLIC_URL", "http://localhost:9000")
        self._public_base = f"{public_ep.rstrip('/')}/{self._bucket}"
        self._s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY", "minioadmin"),
            aws_secret_access_key=os.getenv("AWS_SECRET_KEY", "minioadmin"),
            region_name="us-east-1",
        )
        try:
            self._s3.head_bucket(Bucket=self._bucket)
        except Exception:
            try:
                self._s3.create_bucket(Bucket=self._bucket)
            except Exception:
                pass
        try:
            policy = json.dumps({"Version": "2012-10-17", "Statement": [{"Sid": "PublicRead",
                "Effect": "Allow", "Principal": "*", "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{self._bucket}/*"]}]})
            self._s3.put_bucket_policy(Bucket=self._bucket, Policy=policy)
        except Exception:
            pass

    async def upload(self, data: bytes, key: str, content_type: str = "image/png") -> str:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._s3.put_object(Bucket=self._bucket, Key=key, Body=data, ContentType=content_type),
        )
        return f"{self._public_base}/{key}"


async def _run_creative_generation(campaign_id: str, tenant_id: str) -> None:
    from backend.app.agents.copywriter import CopywriterAgent, CreativeBrief
    from backend.app.agents.scriptwriter import ScriptwriterAgent, ScriptwriterBrief
    from backend.app.agents.image_generator import ImageGeneratorAgent, ImageGenerationBrief
    from backend.app.tools.serpapi import search_competitor_ads

    mongo_client = AsyncIOMotorClient(MONGO_DB_URL)
    try:
        db = mongo_client[MONGO_DB_NAME]
        doc = await db["campaigns"].find_one({"_id": campaign_id, "tenant_id": tenant_id})
        if not doc:
            logger.error("[run_creative_generation] campaign not found: %s", campaign_id)
            return

        concepts = doc.get("concepts", [])
        selected_id = doc.get("selected_concept_id")
        concept = next(
            (c for c in concepts if str(c.get("id", "")) == selected_id),
            concepts[0] if concepts else {},
        )
        mandate = await db["mandates"].find_one(
            {"_id": doc.get("mandate_id"), "tenant_id": tenant_id}
        ) or {}

        # Extract shared brief fields from concept + mandate
        tone_board = concept.get("tone_board", {})
        tone_adjectives = (
            tone_board.get("adjectives", [])
            if isinstance(tone_board, dict)
            else ([tone_board] if isinstance(tone_board, str) else [])
        )
        messaging = concept.get("message_architecture", {})
        channels = [m.get("channel", "") for m in concept.get("channel_mix", [])]

        copy_brief = CreativeBrief(
            campaign_id=campaign_id,
            tenant_id=tenant_id,
            core_concept=concept.get("name", ""),
            campaign_theme=concept.get("campaign_theme", ""),
            tone_adjectives=tone_adjectives,
            visual_direction=concept.get("visual_direction", ""),
            brand_voice=mandate.get("brand_voice", ""),
            primary_cta=messaging.get("primary_cta", ""),
            target_audience=str(
                concept.get("audience_segmentation", {}).get("primary", mandate.get("target_audience", ""))
            ),
            product_details=mandate.get("product_details", ""),
            messaging_rules=messaging.get("messaging_rules", []),
        )

        script_brief = ScriptwriterBrief(
            campaign_id=campaign_id,
            tenant_id=tenant_id,
            script_format="tvc",
            core_concept=copy_brief.core_concept,
            campaign_theme=copy_brief.campaign_theme,
            tone_adjectives=copy_brief.tone_adjectives,
            visual_direction=copy_brief.visual_direction,
            brand_voice=copy_brief.brand_voice,
            target_audience=copy_brief.target_audience,
            product_details=copy_brief.product_details,
            primary_cta=copy_brief.primary_cta,
            messaging_rules=copy_brief.messaging_rules,
        )

        # Step 0: SerpAPI competitor analysis — inform creative prompts
        competitor_insights: dict = {}
        brand_name = mandate.get("brand_name") or mandate.get("name") or ""
        if brand_name:
            try:
                competitor_insights = await search_competitor_ads(brand_name)
                logger.info("[run_creative_generation] SerpAPI insights for %s: channels=%s",
                            brand_name, competitor_insights.get("channels_detected", []))
            except Exception as _serp_exc:
                logger.warning("[run_creative_generation] SerpAPI skipped: %s", _serp_exc)

        copywriter = CopywriterAgent()
        scriptwriter = ScriptwriterAgent()

        try:
            copy_result, script_result = await asyncio.gather(
                copywriter.generate(copy_brief),
                scriptwriter.generate(script_brief),
                return_exceptions=True,
            )

            if isinstance(copy_result, Exception):
                logger.error("[run_creative_generation] copywriter error for %s: %s", campaign_id, copy_result)
                copy_assets = []
            else:
                raw = copy_result.model_dump(mode="json") if hasattr(copy_result, "model_dump") else copy_result
                copy_assets = raw.get("assets", []) if isinstance(raw, dict) else []

            if isinstance(script_result, Exception):
                logger.error("[run_creative_generation] scriptwriter error for %s: %s", campaign_id, script_result)
                script_assets = []
            else:
                raw = script_result.model_dump(mode="json") if hasattr(script_result, "model_dump") else script_result
                def _to_list(val):
                    if isinstance(val, list):
                        return val
                    if isinstance(val, dict):
                        for k in ("scripts", "tvc_scripts", "radio_scripts", "social_video_scripts", "items", "results"):
                            if k in val and isinstance(val[k], list):
                                return val[k]
                        return [val]
                    return []

                def _normalize_script(s: dict) -> dict:
                    # Build readable content string from scenes if content field absent
                    if "content" not in s:
                        lines = []
                        for sc in (s.get("scenes") or []):
                            if isinstance(sc, dict):
                                parts = [f"Scene {sc.get('scene_number', '')}:"]
                                if sc.get("description"):
                                    parts.append(sc["description"])
                                if sc.get("action"):
                                    parts.append(f"Action: {sc['action']}")
                                if sc.get("dialogue"):
                                    parts.append(f'"{sc["dialogue"]}"')
                                lines.append("\n".join(parts))
                        if not lines and s.get("directors_note"):
                            lines.append(s["directors_note"])
                        s = dict(s, content="\n\n".join(lines) if lines else "Script content not available")
                    if "id" not in s:
                        s = dict(s, id=str(uuid4()))
                    if "format" not in s:
                        s = dict(s, format="tvc_vo")
                    if "duration_estimate" not in s:
                        dur = s.get("duration_label") or (
                            f"{s.get('total_duration_seconds', 30)}s"
                            if s.get("total_duration_seconds") else "30s"
                        )
                        s = dict(s, duration_estimate=dur)
                    if "approved" not in s:
                        s = dict(s, approved=None)
                    if "revision_count" not in s:
                        s = dict(s, revision_count=0)
                    return s

                script_assets = [_normalize_script(s) for s in _to_list(raw)]

            # Step 3: Generate images via Stability AI (square / landscape / portrait)
            image_assets = []
            try:
                storage = _MinioStorageClient()
                image_agent = ImageGeneratorAgent()
                competitor_style = ", ".join(competitor_insights.get("messaging_samples", [])[:2])
                img_briefs = [
                    ImageGenerationBrief(
                        campaign_id=campaign_id,
                        tenant_id=tenant_id,
                        image_format=fmt,
                        visual_direction=concept.get("visual_direction", copy_brief.campaign_theme),
                        brand_palette=mandate.get("brand_colors", []),
                        tone_adjectives=tone_adjectives,
                        campaign_theme=copy_brief.campaign_theme,
                        style_notes=competitor_style,
                    )
                    for fmt in ("square", "landscape", "portrait")
                ]
                img_results = await asyncio.gather(
                    *[image_agent.generate(b, storage_client=storage) for b in img_briefs],
                    return_exceptions=True,
                )
                for fmt, res in zip(("square", "landscape", "portrait"), img_results):
                    if isinstance(res, Exception):
                        logger.error("[run_creative_generation] image %s failed: %s", fmt, res)
                    else:
                        image_assets.append({
                            "id": str(uuid4()),
                            "format": fmt,
                            "url": res.asset_url,
                            "approved": None,
                            "revision_count": 0,
                        })
                logger.info("[run_creative_generation] images generated: %d", len(image_assets))
            except Exception as _img_exc:
                logger.error("[run_creative_generation] image generation block failed: %s", _img_exc)

            await db["campaigns"].update_one(
                {"_id": campaign_id, "tenant_id": tenant_id},
                {"$set": {
                    "status": "creative_ready",
                    "creative_assets": {
                        "campaign_id": campaign_id,
                        "stage": "internal_review",
                        "copy": copy_assets,
                        "scripts": script_assets,
                        "images": image_assets,
                        "audio": [],
                    },
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }},
            )
            logger.info(
                "[run_creative_generation] complete for %s copy=%d scripts=%d images=%d",
                campaign_id, len(copy_assets), len(script_assets), len(image_assets),
            )
            # Step 4: Chain Runway video generation using first image as reference
            try:
                run_video_generation.delay(campaign_id, tenant_id)
                logger.info("[run_creative_generation] queued run_video_generation for %s", campaign_id)
            except Exception as _vid_exc:
                logger.warning("[run_creative_generation] video task dispatch failed: %s", _vid_exc)
        except Exception as exc:
            logger.error("[run_creative_generation] failed for %s: %s", campaign_id, exc)
            await db["campaigns"].update_one(
                {"_id": campaign_id, "tenant_id": tenant_id},
                {"$set": {
                    "error": f"creative generation failed: {exc}",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }},
            )
    finally:
        mongo_client.close()


@shared_task(bind=True, max_retries=2)
def run_creative_generation(self, campaign_id: str, tenant_id: str) -> None:
    """Celery task: run AGT-07 + AGT-08 to generate creative assets for a campaign."""
    logger.info("[run_creative_generation] start campaign_id=%s", campaign_id)
    try:
        asyncio.run(_run_creative_generation(campaign_id, tenant_id))
    except Exception as exc:
        logger.error("[run_creative_generation] error %s: %s", campaign_id, exc)
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
