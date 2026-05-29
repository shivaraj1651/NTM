"""
Celery tasks for Phase 2 competitive intelligence metrics gathering.

Async tasks for fetching competitor metrics from APIs, managing cache,
and synthesizing whitespace opportunities via LLM.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from celery import shared_task
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorClient
from anthropic import AsyncAnthropic
from pydantic import BaseModel, ValidationError

from backend.app.schemas.competitive_intel import (
    CIReport,
    CompetitorMetrics,
    ChannelMetrics,
    WhitespaceOpportunities,
)
from backend.app.tools.serpapi import search_competitor_ads
from backend.app.tools.meta_ads import lookup_meta_ads

logger = logging.getLogger(__name__)

# Configuration from environment
MONGO_DB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGODB_DB", "ntm")
MONGO_COLLECTION_CI_REPORTS = os.getenv("MONGO_COLLECTION_CI_REPORTS", "ci_reports")
MONGO_COLLECTION_COMPETITOR_CACHE = os.getenv("MONGO_COLLECTION_COMPETITOR_CACHE", "competitor_cache")
CACHE_TTL_METRICS_DAYS = int(os.getenv("CACHE_TTL_METRICS_DAYS", "7"))
LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4-20250514")


# Pydantic model for LLM synthesis response validation
class SynthesisResponse(BaseModel):
    """Validated response structure from LLM synthesis."""
    untapped_channels: List[str]
    messaging_gaps: List[str]
    geographic_gaps: List[str]
    market_concentration: str


async def get_mongo_db() -> AsyncIOMotorDatabase:
    """
    Get MongoDB connection via Motor.

    Returns:
        AsyncIOMotorDatabase: Async MongoDB database connection
    """
    client = AsyncIOMotorClient(MONGO_DB_URL)
    db = client[MONGO_DB_NAME]
    return db


async def get_competitor_cache(
    db: AsyncIOMotorDatabase, competitor_name: str, tenant_id: str
) -> Optional[Dict[str, Any]]:
    """
    Look up cached competitor metrics, check freshness.

    Args:
        db: MongoDB database connection
        competitor_name: Name of competitor to look up
        tenant_id: Tenant ID for multi-tenancy filtering

    Returns:
        Cached metrics dict if fresh (TTL not expired), None otherwise
    """
    try:
        cache_collection = db[MONGO_COLLECTION_COMPETITOR_CACHE]
        cached = await cache_collection.find_one({
            "competitor_name": competitor_name,
            "tenant_id": tenant_id,
        })

        if not cached:
            logger.info(f"Cache miss for competitor: {competitor_name}")
            return None

        # Check TTL (expiry)
        created_at = cached.get("created_at")
        if not created_at:
            logger.warning(f"Cached entry for {competitor_name} missing created_at")
            return None

        # Calculate age with timezone awareness
        now = datetime.now(timezone.utc)
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
            # Ensure timezone-aware
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)

        age_days = (now - created_at).days
        if age_days > CACHE_TTL_METRICS_DAYS:
            logger.info(f"Cache expired for {competitor_name} (age: {age_days} days)")
            return None

        logger.info(f"Cache hit for {competitor_name} (age: {age_days} days)")
        return cached.get("metrics")

    except Exception as e:
        logger.error(f"Error retrieving cache for {competitor_name}: {e}")
        return None


async def save_competitor_cache(
    db: AsyncIOMotorDatabase,
    competitor_name: str,
    channels: Dict[str, Any],
    messaging_themes: List[str],
    geographic_focus: List[str],
    estimated_spend: Optional[float],
    tenant_id: str,
) -> None:
    """
    Save competitor metrics to cache.

    Args:
        db: MongoDB database connection
        competitor_name: Name of competitor
        channels: Dict of channel metrics
        messaging_themes: List of messaging themes
        geographic_focus: List of geographic regions
        estimated_spend: Estimated annual spend
        tenant_id: Tenant ID for multi-tenancy filtering
    """
    try:
        cache_collection = db[MONGO_COLLECTION_COMPETITOR_CACHE]

        cache_doc = {
            "competitor_name": competitor_name,
            "tenant_id": tenant_id,
            "created_at": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(),
            "metrics": {
                "channels": channels,
                "messaging_themes": messaging_themes,
                "geographic_focus": geographic_focus,
                "estimated_spend": estimated_spend,
            },
        }

        # Upsert to avoid duplicates
        await cache_collection.update_one(
            {"competitor_name": competitor_name, "tenant_id": tenant_id},
            {"$set": cache_doc},
            upsert=True,
        )
        logger.info(f"Cached metrics for {competitor_name}")

    except Exception as e:
        logger.error(f"Error saving cache for {competitor_name}: {e}")


async def fetch_competitor_metrics_single(
    competitor_name: str,
    geography: List[str],
    db: AsyncIOMotorDatabase,
    tenant_id: str,
) -> Dict[str, Any]:
    """
    Fetch metrics for ONE competitor from APIs or cache.

    Attempts cache lookup first. If miss or expired, calls SerpAPI + Meta APIs
    in parallel, then saves to cache.

    Args:
        competitor_name: Competitor name to search
        geography: List of geographic regions
        db: MongoDB database connection
        tenant_id: Tenant ID for multi-tenancy filtering

    Returns:
        Dict with channels, messaging_themes, geographic_focus, estimated_spend
        If errors occur, returns partial results with best-effort nulls
    """
    # Try cache first
    cached = await get_competitor_cache(db, competitor_name, tenant_id)
    if cached:
        return cached

    logger.info(f"Fetching fresh metrics for {competitor_name}")

    try:
        # Call both APIs in parallel
        serpapi_result, meta_result = await asyncio.gather(
            search_competitor_ads(competitor_name),
            lookup_meta_ads(competitor_name),
            return_exceptions=True,
        )

        # Handle exceptions from gather
        if isinstance(serpapi_result, Exception):
            logger.error(f"SerpAPI error for {competitor_name}: {serpapi_result}")
            serpapi_result = {
                "channels_detected": [],
                "messaging_samples": [],
                "error": str(serpapi_result),
            }

        if isinstance(meta_result, Exception):
            logger.error(f"Meta API error for {competitor_name}: {meta_result}")
            meta_result = {
                "ads_found": 0,
                "placements": [],
                "estimated_monthly_spend": None,
                "error": str(meta_result),
            }

        # Build channels dict from results
        channels: Dict[str, ChannelMetrics] = {}

        # Google Ads / SerpAPI channels
        if "google_ads" in serpapi_result.get("channels_detected", []):
            channels["google_ads"] = ChannelMetrics(
                presence=True,
                estimated_monthly_spend=None,
                estimated_monthly_impressions=None,
                placements=["search"],
                primary_keywords=serpapi_result.get("messaging_samples", []),
                primary_audiences=[],
            )

        # Meta / Facebook channels
        if meta_result.get("ads_found", 0) > 0:
            channels["meta"] = ChannelMetrics(
                presence=True,
                estimated_monthly_spend=meta_result.get("estimated_monthly_spend"),
                estimated_monthly_impressions=meta_result.get("impressions_estimate"),
                placements=meta_result.get("placements", ["feed", "stories"]),
                primary_keywords=[],
                primary_audiences=meta_result.get("primary_audiences", []),
            )

        # Aggregate messaging themes from both sources
        messaging_themes = list(
            set(
                serpapi_result.get("messaging_samples", [])
                + meta_result.get("primary_audiences", [])
            )
        )[:5]

        # Use provided geography
        geographic_focus = geography if geography else []

        # Calculate estimated spend (Meta + extrapolate from detection)
        estimated_spend = meta_result.get("estimated_monthly_spend", 0)
        if estimated_spend:
            estimated_spend = estimated_spend * 12  # Annual

        result = {
            "channels": channels,
            "messaging_themes": messaging_themes,
            "geographic_focus": geographic_focus,
            "estimated_spend": estimated_spend,
        }

        # Save to cache
        await save_competitor_cache(
            db,
            competitor_name,
            channels,
            messaging_themes,
            geographic_focus,
            estimated_spend,
            tenant_id,
        )

        return result

    except Exception as e:
        logger.error(f"Error fetching metrics for {competitor_name}: {e}")
        # Return partial/empty result on error
        return {
            "channels": {},
            "messaging_themes": [],
            "geographic_focus": geography,
            "estimated_spend": None,
        }


async def synthesize_competitive_report(
    competitors_metrics: List[Dict[str, Any]],
    mandate: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Synthesize competitive report using Claude Sonnet LLM.

    Takes raw competitor metrics and mandate to produce:
    - whitespace_opportunities (untapped channels, messaging gaps, geographic gaps)
    - market_concentration (fragmented/concentrated/oligopoly)

    Args:
        competitors_metrics: List of competitor metric dicts
        mandate: Mandate dict with campaign_concept, geography, budget

    Returns:
        Dict with whitespace_opportunities and market_concentration
    """
    client = AsyncAnthropic()

    # Extract mandate context
    campaign_objective = mandate.get("campaign_concept", {}).get("objective", "")
    target_audience = mandate.get("campaign_concept", {}).get("target_audience", "")
    country_list = mandate.get("geography", {}).get("country_list", [])
    budget = mandate.get("budget", {}).get("total_amount", 0)

    # Prepare competitor summary for LLM
    competitor_summary = []
    for comp in competitors_metrics:
        summary = {
            "channels": list(comp.get("channels", {}).keys()),
            "messaging_themes": comp.get("messaging_themes", []),
            "geographic_focus": comp.get("geographic_focus", []),
            "estimated_spend": comp.get("estimated_spend"),
        }
        competitor_summary.append(summary)

    system_prompt = """You are a competitive intelligence analyst. Analyze the competitive landscape and identify whitespace opportunities.

Respond ONLY with valid JSON, no markdown. Do not wrap in code blocks.

Return exactly this structure:
{
  "untapped_channels": ["list of advertising channels not used by competitors"],
  "messaging_gaps": ["list of messaging angles/themes not covered"],
  "geographic_gaps": ["list of geographic regions not targeted"],
  "market_concentration": "fragmented" or "concentrated" or "oligopoly"
}"""

    user_prompt = f"""Analyze this competitive landscape and identify whitespace opportunities.

Campaign Objective: {campaign_objective}
Target Audience: {target_audience}
Geographic Focus: {country_list}
Budget: ${budget}

Competitor Activity:
{json.dumps(competitor_summary, indent=2)}

Identify untapped channels, messaging gaps, and geographic gaps. Also assess market concentration."""

    try:
        response = await client.messages.create(
            model=LLM_MODEL,
            max_tokens=2000,
            temperature=0.2,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception as e:
        logger.error(f"LLM synthesis call failed: {e}")
        # Return fallback structure
        return {
            "untapped_channels": [],
            "messaging_gaps": [],
            "geographic_gaps": [],
            "market_concentration": "unknown",
            "error": str(e),
        }

    # Parse LLM response
    if not response.content or not response.content[0].text:
        logger.error("LLM synthesis returned empty response")
        return {
            "untapped_channels": [],
            "messaging_gaps": [],
            "geographic_gaps": [],
            "market_concentration": "unknown",
            "error": "LLM returned empty response",
        }

    response_text = response.content[0].text
    try:
        result = json.loads(response_text)
        # Validate against Pydantic model
        validated = SynthesisResponse(**result)
        return validated.model_dump()
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM synthesis JSON: {response_text}")
        return {
            "untapped_channels": [],
            "messaging_gaps": [],
            "geographic_gaps": [],
            "market_concentration": "unknown",
            "error": f"LLM response was not valid JSON: {str(e)}",
        }
    except ValidationError as e:
        logger.error(f"LLM response validation failed: {e}")
        return {
            "untapped_channels": [],
            "messaging_gaps": [],
            "geographic_gaps": [],
            "market_concentration": "unknown",
            "error": f"LLM response validation failed: {str(e)}",
        }


async def _async_fetch_competitor_metrics(
    mandate_id: str,
    competitor_names: List[str],
    mandate_dict: Dict[str, Any],
    tenant_id: str,
    job_id: str,
) -> None:
    """
    Internal async orchestration for Phase 2 competitive intelligence.

    Orchestrates Phase 2 of competitive intelligence:
    1. Connect to MongoDB
    2. Fetch metrics for all competitors in parallel
    3. Synthesize with LLM to identify whitespace
    4. Build full CIReport dict
    5. Store in MongoDB ci_reports collection

    Args:
        mandate_id: Mandate ID
        competitor_names: List of competitor names to fetch
        mandate_dict: Full mandate dict
        tenant_id: Tenant ID for multi-tenancy
        job_id: Job ID for tracking
    """
    logger.info(f"[Job {job_id}] Starting metrics fetch for {len(competitor_names)} competitors")

    # Connect to MongoDB
    db = await get_mongo_db()

    # Extract geography from mandate
    geography = mandate_dict.get("geography", {}).get("country_list", [])

    # Fetch metrics for all competitors in parallel
    tasks = [
        fetch_competitor_metrics_single(comp_name, geography, db, tenant_id)
        for comp_name in competitor_names
    ]
    competitors_metrics = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out exceptions from results
    exceptions = [m for m in competitors_metrics if isinstance(m, Exception)]
    if exceptions:
        logger.warning(f"[Job {job_id}] {len(exceptions)} competitor fetch(es) had errors")

    competitors_metrics = [m for m in competitors_metrics if not isinstance(m, Exception)]

    logger.info(f"[Job {job_id}] Retrieved metrics for {len(competitors_metrics)} competitors")

    # Synthesize competitive report with LLM
    synthesis_result = await synthesize_competitive_report(
        competitors_metrics, mandate_dict
    )

    # Build CompetitorMetrics list (with confidence scores)
    competitor_objects = []
    for idx, (comp_name, metrics) in enumerate(
        zip(competitor_names, competitors_metrics)
    ):
        # Assign confidence based on data completeness
        channel_count = len(metrics.get("channels", {}))
        has_spend = metrics.get("estimated_spend") is not None
        confidence = min(
            100,
            30 + (channel_count * 20) + (40 if has_spend else 0),
        )

        competitor_obj = CompetitorMetrics(
            name=comp_name,
            confidence_score=confidence,
            channels=metrics.get("channels", {}),
            messaging_themes=metrics.get("messaging_themes", []),
            geographic_focus=metrics.get("geographic_focus", []),
            estimated_annual_spend=metrics.get("estimated_spend"),
            data_sources=["serpapi", "meta_ads"],
            data_confidence="medium" if channel_count > 0 else "low",
        )
        competitor_objects.append(competitor_obj)

    # Build final CIReport
    ci_report = CIReport(
        mandate_id=mandate_id,
        job_id=job_id,
        generated_at=datetime.now(timezone.utc),
        tenant_id=tenant_id,
        competitors=competitor_objects,
        whitespace_opportunities=WhitespaceOpportunities(
            untapped_channels=synthesis_result.get("untapped_channels", []),
            messaging_gaps=synthesis_result.get("messaging_gaps", []),
            geographic_gaps=synthesis_result.get("geographic_gaps", []),
        ),
        market_concentration=synthesis_result.get("market_concentration", "unknown"),
        status="complete",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    # Store in MongoDB
    ci_reports_collection = db[MONGO_COLLECTION_CI_REPORTS]
    report_dict = ci_report.model_dump(mode="json")

    result = await ci_reports_collection.insert_one(report_dict)
    logger.info(
        f"[Job {job_id}] Stored CI report in MongoDB with ID: {result.inserted_id}"
    )


@shared_task(bind=True, max_retries=3)
def fetch_competitor_metrics(
    self,
    mandate_id: str,
    competitor_names: List[str],
    mandate_dict: Dict[str, Any],
    tenant_id: str,
    job_id: str,
) -> None:
    """
    Celery task: Fetch competitor metrics and synthesize CI report.

    Synchronous wrapper that uses asyncio.run() to execute async orchestration.
    On error: store partial report with status='failed', retry 3x.

    Args:
        mandate_id: Mandate ID
        competitor_names: List of competitor names to fetch
        mandate_dict: Full mandate dict
        tenant_id: Tenant ID for multi-tenancy
        job_id: Job ID for tracking

    Returns:
        None (writes to MongoDB on completion)
    """
    try:
        # Execute async orchestration in sync context
        asyncio.run(
            _async_fetch_competitor_metrics(
                mandate_id, competitor_names, mandate_dict, tenant_id, job_id
            )
        )
    except Exception as e:
        logger.error(f"[Job {job_id}] Error in fetch_competitor_metrics: {e}")

        # Try to store partial report with failed status
        try:
            db = asyncio.run(get_mongo_db())
            ci_reports_collection = db[MONGO_COLLECTION_CI_REPORTS]

            partial_report = {
                "mandate_id": mandate_id,
                "job_id": job_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "tenant_id": tenant_id,
                "competitors": [],
                "whitespace_opportunities": {
                    "untapped_channels": [],
                    "messaging_gaps": [],
                    "geographic_gaps": [],
                },
                "market_concentration": "unknown",
                "status": "failed",
                "error": str(e),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            # Insert without awaiting
            asyncio.run(ci_reports_collection.insert_one(partial_report))
            logger.info(f"[Job {job_id}] Stored partial failed report in MongoDB")
        except Exception as db_error:
            logger.error(f"[Job {job_id}] Failed to store partial report: {db_error}")

        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=2 ** self.request.retries)


async def _run_competitive_intel_pipeline(mandate_id: str, tenant_id: str) -> None:
    """Async: fetch mandate + client from MongoDB, run AGT-02 phase 1, dispatch phase 2."""
    from backend.app.agents.competitive_intel import competitive_intel_agent
    import uuid

    mongo_client = AsyncIOMotorClient(os.getenv("MONGODB_URL", "mongodb://localhost:27017"))
    try:
        db = mongo_client[os.getenv("MONGODB_DB", "ntm")]
        mandate = await db["mandates"].find_one({"_id": mandate_id, "tenant_id": tenant_id})
        if not mandate:
            logger.warning("[run_competitive_intel_pipeline] mandate not found: %s", mandate_id)
            return
        client_id = mandate.get("client_id")
        client_profile = {}
        if client_id:
            client_profile = await db["clients"].find_one({"_id": client_id, "tenant_id": tenant_id}) or {}
    finally:
        mongo_client.close()

    ci_initial = await competitive_intel_agent(
        mandate=mandate,
        client_profile=client_profile,
        mandate_id=mandate_id,
        tenant_id=tenant_id,
    )
    competitor_names = [c.name for c in ci_initial.competitors]
    job_id = ci_initial.job_id or str(uuid.uuid4())

    fetch_competitor_metrics.delay(
        mandate_id=mandate_id,
        competitor_names=competitor_names,
        mandate_dict=mandate,
        tenant_id=tenant_id,
        job_id=job_id,
    )
    logger.info("[run_competitive_intel_pipeline] dispatched phase-2 for mandate %s, job %s", mandate_id, job_id)


@shared_task(bind=True, max_retries=2)
def run_competitive_intel_pipeline(self, mandate_id: str, tenant_id: str) -> None:
    """Celery task: auto-triggered after AGT-01; runs CI phase 1 then enqueues phase 2."""
    try:
        asyncio.run(_run_competitive_intel_pipeline(mandate_id, tenant_id))
    except Exception as e:
        logger.error("[run_competitive_intel_pipeline] failed for %s: %s", mandate_id, e)
        raise self.retry(exc=e, countdown=2 ** self.request.retries)
