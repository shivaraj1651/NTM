# backend/app/routers/digital_activator.py
import logging
import os
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from backend.app.core.auth import current_user
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

_PLATFORM_TASK_MAP = {
    "google_ads": platform_activate_google,
    "meta_ads": platform_activate_meta,
    "linkedin_ads": platform_activate_linkedin,
}


async def get_db() -> AsyncIOMotorDatabase:
    client = AsyncIOMotorClient(os.getenv("MONGO_DB_URL", "mongodb://localhost:27017"))
    return client[os.getenv("MONGO_DB_NAME", "ntm")]


@router.post("/campaigns/{campaign_id}/activate", response_model=JobQueuedResponse, status_code=202)
async def activate_campaign(
    campaign_id: str,
    user: User = Depends(require_role(DIGITAL_ROLES)),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> JobQueuedResponse:
    svc = CampaignService(db)
    campaign = await svc.get(campaign_id, tenant_id)

    job_id = str(uuid4())
    activation_plan = campaign.get("activation_plan") or [] if isinstance(campaign, dict) else (campaign.activation_plan or [])

    for act in activation_plan:
        channel = act.get("channel") if isinstance(act, dict) else getattr(act, "channel", None)
        task_fn = _PLATFORM_TASK_MAP.get(channel)
        if task_fn:
            act_payload = dict(act) if isinstance(act, dict) else act.model_dump()
            act_payload["tenant_id"] = tenant_id
            task_fn.delay(
                activation=act_payload,
                platform_config={},
                creative_url="",
            )
            logger.info(
                "Queued activation task",
                extra={"channel": channel, "campaign_id": campaign_id},
            )

    return JobQueuedResponse(job_id=job_id, campaign_id=campaign_id)
