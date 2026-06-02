# backend/app/routers/digital_activator.py
import logging
import os
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pydantic import BaseModel

from backend.app.core.dependencies import get_current_tenant, require_role
from backend.app.core.models import User, UserRole
from backend.app.services.campaign_service import CampaignService
from backend.app.tools.google_ads import activate_google
from backend.app.tools.meta_ads import activate_meta
from backend.app.tools.linkedin_ads import activate_linkedin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["digital-activator"])

DIGITAL_ROLES = [
    UserRole.CAMPAIGN_MANAGER,
    UserRole.TENANT_ADMIN,
    UserRole.PLATFORM_ADMIN,
]

_GOOGLE_KEYWORDS = ("google", "search", "display", "youtube", "video", "programmatic", "gdn")
_META_KEYWORDS = ("meta", "facebook", "instagram", "social", "reels", "stories")
_LINKEDIN_KEYWORDS = ("linkedin",)


class ActivationResponse(BaseModel):
    job_id: str
    campaign_id: str
    activation_results: dict


def _channel_to_platform(channel_enum: str | None, channel: str | None) -> str | None:
    if channel_enum:
        lower = channel_enum.lower()
        if lower in ("google_ads", "meta_ads", "linkedin_ads"):
            return lower
        if any(k in lower for k in _GOOGLE_KEYWORDS):
            return "google_ads"
        if any(k in lower for k in _META_KEYWORDS):
            return "meta_ads"
        if any(k in lower for k in _LINKEDIN_KEYWORDS):
            return "linkedin_ads"
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


@router.post("/campaigns/{campaign_id}/activate", response_model=ActivationResponse, status_code=202)
async def activate_campaign(
    campaign_id: str,
    _: User = Depends(require_role(DIGITAL_ROLES)),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ActivationResponse:
    svc = CampaignService(db)
    campaign = await svc.get(campaign_id, tenant_id)
    campaign_dict = campaign if isinstance(campaign, dict) else campaign.model_dump()

    activation_plan = campaign_dict.get("activation_plan") or []

    # Extract creative URL (prefer landscape image)
    creative_assets = campaign_dict.get("creative_assets") or {}
    images = creative_assets.get("images") or []
    landscape = next((i for i in images if i.get("format") == "landscape"), None)
    creative_url = (landscape or (images[0] if images else {})).get("url", "")

    # Extract selected concept for ad copy
    concepts = campaign_dict.get("concepts", [])
    selected_id = campaign_dict.get("selected_concept_id")
    concept = next(
        (c for c in concepts if str(c.get("id", "")) == selected_id),
        concepts[0] if concepts else {},
    )
    tone_board = concept.get("tone_board", {}) if isinstance(concept.get("tone_board"), dict) else {}
    messaging = concept.get("message_architecture", {}) if isinstance(concept.get("message_architecture"), dict) else {}

    base_platform_config = {
        "tagline":        concept.get("tagline", ""),
        "master_message": messaging.get("master_message", ""),
        "concept_name":   concept.get("name", ""),
        "description":    tone_board.get("visual_direction", "") or messaging.get("master_message", ""),
        "objective":      campaign_dict.get("mandate", {}).get("objective", "awareness"),
        "geo_locations":  {"countries": ["US"]},
    }

    # Aggregate budget per platform
    platform_budgets: dict[str, float] = {}
    platform_activations: dict[str, dict] = {}
    for act in activation_plan:
        act_dict = dict(act) if isinstance(act, dict) else act.model_dump()
        platform = _channel_to_platform(
            act_dict.get("channel_enum") or act_dict.get("channelEnum"),
            act_dict.get("channel"),
        )
        if platform:
            cost = float(act_dict.get("cost_estimated") or act_dict.get("budget") or 0)
            platform_budgets[platform] = platform_budgets.get(platform, 0) + cost
            if platform not in platform_activations:
                platform_activations[platform] = act_dict

    # Default google+meta split if no recognised platform channels
    if not platform_activations and activation_plan:
        total_budget = sum(
            float((dict(a) if isinstance(a, dict) else a.model_dump()).get("cost_estimated") or 0)
            for a in activation_plan
        )
        base_name = base_platform_config["concept_name"] or f"Campaign {campaign_id[:8]}"
        platform_activations["google_ads"] = {
            "id": str(uuid4()), "name": base_name,
            "cost_estimated": total_budget * 0.5, "channel": "Google Ads Search",
        }
        platform_activations["meta_ads"] = {
            "id": str(uuid4()), "name": base_name,
            "cost_estimated": total_budget * 0.5, "channel": "Meta Ads",
        }
        platform_budgets["google_ads"] = total_budget * 0.5
        platform_budgets["meta_ads"]   = total_budget * 0.5

    # ── Activate each platform synchronously ──────────────────────────────────
    final_results: dict[str, dict] = {}

    for platform, act_payload in platform_activations.items():
        if "id" not in act_payload or not act_payload["id"]:
            act_payload["id"] = str(uuid4())
        act_payload["cost_estimated"] = platform_budgets.get(platform, act_payload.get("cost_estimated", 0))

        logger.info(
            "Activating %s synchronously budget=%.0f campaign=%s",
            platform, act_payload["cost_estimated"], campaign_id,
        )

        if platform == "google_ads":
            result = await activate_google(act_payload, base_platform_config, creative_url)
        elif platform == "meta_ads":
            result = await activate_meta(act_payload, base_platform_config, creative_url)
        elif platform == "linkedin_ads":
            result = await activate_linkedin(act_payload, base_platform_config, creative_url)
        else:
            result = {"status": "failed", "error": f"Unknown platform: {platform}"}

        final_results[platform] = result
        logger.info(
            "Platform %s result: status=%s campaign_id=%s",
            platform, result.get("status"), result.get("campaign_id"),
        )

    # Write results to MongoDB so campaign GET returns them
    if final_results:
        try:
            await db["campaigns"].update_one(
                {"_id": campaign_id, "tenant_id": tenant_id},
                {"$set": {
                    "activation_results": final_results,
                    "updated_at": datetime.now(UTC).isoformat(),
                }},
            )
        except Exception as exc:
            logger.warning("Failed to write activation_results to MongoDB: %s", exc)

    if not final_results:
        logger.warning("No platforms activated for campaign %s", campaign_id)

    return ActivationResponse(
        job_id=str(uuid4()),
        campaign_id=campaign_id,
        activation_results=final_results,
    )
