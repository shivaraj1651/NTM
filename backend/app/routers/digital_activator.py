# backend/app/routers/digital_activator.py
import logging
import os
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from backend.app.core.dependencies import get_current_tenant, require_role
from backend.app.core.models import User, UserRole
from backend.app.schemas.jobs import JobQueuedResponse
from backend.app.services.campaign_service import CampaignService
from backend.app.tasks.activation_tasks import (
    platform_activate_google,
    platform_activate_meta,
    platform_activate_linkedin,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["digital-activator"])

DIGITAL_ROLES = [
    UserRole.CAMPAIGN_MANAGER,
    UserRole.TENANT_ADMIN,
    UserRole.PLATFORM_ADMIN,
]

# Map channel_enum values and common channel name patterns to platform tasks
_ENUM_TASK_MAP = {
    "google_ads": platform_activate_google,
    "meta_ads": platform_activate_meta,
    "linkedin_ads": platform_activate_linkedin,
}

# Broader pattern matching for human-readable channel names from AGT-04
_GOOGLE_KEYWORDS = ("google", "search", "display", "youtube", "video", "programmatic", "gdn")
_META_KEYWORDS = ("meta", "facebook", "instagram", "social", "reels", "stories")
_LINKEDIN_KEYWORDS = ("linkedin",)


def _channel_to_platform(channel_enum: str | None, channel: str | None) -> str | None:
    """Return platform key (google_ads / meta_ads / linkedin_ads) or None."""
    # Prefer machine-readable enum
    if channel_enum:
        lower = channel_enum.lower()
        if lower in _ENUM_TASK_MAP:
            return lower
        if any(k in lower for k in _GOOGLE_KEYWORDS):
            return "google_ads"
        if any(k in lower for k in _META_KEYWORDS):
            return "meta_ads"
        if any(k in lower for k in _LINKEDIN_KEYWORDS):
            return "linkedin_ads"
    # Fall back to human-readable channel name
    if channel:
        lower = channel.lower()
        if any(k in lower for k in _GOOGLE_KEYWORDS):
            return "google_ads"
        if any(k in lower for k in _META_KEYWORDS):
            return "meta_ads"
        if any(k in lower for k in _LINKEDIN_KEYWORDS):
            return "linkedin_ads"
    return None


async def get_db() -> AsyncIOMotorDatabase:
    mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    mongo_db_name = os.getenv("MONGODB_DB", "ntm")
    client = AsyncIOMotorClient(mongo_url)
    return client[mongo_db_name]


@router.post("/campaigns/{campaign_id}/activate", response_model=JobQueuedResponse, status_code=202)
async def activate_campaign(
    campaign_id: str,
    _: User = Depends(require_role(DIGITAL_ROLES)),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> JobQueuedResponse:
    svc = CampaignService(db)
    campaign = await svc.get(campaign_id, tenant_id)

    job_id = str(uuid4())
    campaign_dict = campaign if isinstance(campaign, dict) else campaign.model_dump()
    activation_plan = campaign_dict.get("activation_plan") or []

    # ── Extract creative URL (prefer landscape image for display, fallback to first) ──
    creative_assets = campaign_dict.get("creative_assets") or {}
    images = creative_assets.get("images") or []
    landscape = next((i for i in images if i.get("format") == "landscape"), None)
    creative_url = (landscape or (images[0] if images else {})).get("url", "")

    # ── Extract selected concept for ad copy ──
    concepts = campaign_dict.get("concepts", [])
    selected_id = campaign_dict.get("selected_concept_id")
    concept = next(
        (c for c in concepts if str(c.get("id", "")) == selected_id),
        concepts[0] if concepts else {},
    )
    tone_board = concept.get("tone_board", {}) if isinstance(concept.get("tone_board"), dict) else {}
    messaging = concept.get("message_architecture", {}) if isinstance(concept.get("message_architecture"), dict) else {}
    tagline        = concept.get("tagline", "")
    master_message = messaging.get("master_message", "")
    concept_name   = concept.get("name", "")
    visual_dir     = tone_board.get("visual_direction", "")
    primary_audience = str(concept.get("audience_segmentation", {}).get("primary", ""))
    mandate_objective = campaign_dict.get("mandate", {}).get("objective", "awareness")

    # Build platform_config carrying concept data for ad copy + basic targeting
    base_platform_config = {
        "tagline":        tagline,
        "master_message": master_message,
        "concept_name":   concept_name,
        "description":    visual_dir or master_message,
        "objective":      mandate_objective,
        "geo_locations":  {"countries": ["US"]},
    }

    # ── Aggregate budget per platform ──
    platform_budgets: dict[str, float] = {}
    platform_activations: dict[str, dict] = {}

    for act in activation_plan:
        act_dict = dict(act) if isinstance(act, dict) else act.model_dump()
        channel_enum = act_dict.get("channel_enum") or act_dict.get("channelEnum")
        channel = act_dict.get("channel")
        platform = _channel_to_platform(channel_enum, channel)
        if platform:
            cost = float(act_dict.get("cost_estimated") or act_dict.get("budget") or 0)
            platform_budgets[platform] = platform_budgets.get(platform, 0) + cost
            if platform not in platform_activations:
                platform_activations[platform] = act_dict

    # Default to google + meta split if no platform channels recognised
    if not platform_activations and activation_plan:
        total_budget = sum(
            float((dict(a) if isinstance(a, dict) else a.model_dump()).get("cost_estimated") or 0)
            for a in activation_plan
        )
        base_name = concept_name or campaign_dict.get("name") or f"Campaign {campaign_id[:8]}"
        platform_activations["google_ads"] = {
            "id": str(uuid4()), "name": base_name,
            "cost_estimated": total_budget * 0.5, "channel": "Google Ads Search",
        }
        platform_activations["meta_ads"] = {
            "id": str(uuid4()), "name": base_name,
            "cost_estimated": total_budget * 0.5, "channel": "Meta Ads",
        }
        platform_budgets["google_ads"] = total_budget * 0.5
        platform_budgets["meta_ads"] = total_budget * 0.5

    # ── Dispatch one task per platform ──
    dispatched = []
    initial_results: dict[str, dict] = {}

    for platform, act_payload in platform_activations.items():
        task_fn = _ENUM_TASK_MAP.get(platform)
        if not task_fn:
            continue
        if "id" not in act_payload or not act_payload["id"]:
            act_payload["id"] = str(uuid4())
        act_payload["tenant_id"] = tenant_id
        act_payload["campaign_id"] = campaign_id  # so task can write back to MongoDB
        act_payload["cost_estimated"] = platform_budgets.get(platform, act_payload.get("cost_estimated", 0))

        task_fn.delay(
            activation=act_payload,
            platform_config=base_platform_config,
            creative_url=creative_url,
        )
        dispatched.append(platform)
        initial_results[platform] = {"status": "queued", "campaign_id": None, "ad_id": None}
        logger.info(
            "Queued %s activation task budget=%.0f campaign=%s",
            platform, act_payload["cost_estimated"], campaign_id,
        )

    # Write initial queued state to MongoDB so frontend can poll for updates
    if initial_results:
        try:
            from datetime import datetime, timezone
            await db["campaigns"].update_one(
                {"_id": campaign_id, "tenant_id": tenant_id},
                {"$set": {
                    "activation_results": initial_results,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }},
            )
        except Exception as _e:
            logger.warning("Failed to initialise activation_results in MongoDB: %s", _e)

    if not dispatched:
        logger.warning("No platforms activated for campaign %s — no matching channels", campaign_id)

    return JobQueuedResponse(job_id=job_id, campaign_id=campaign_id)
