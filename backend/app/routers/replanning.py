import logging
import os
from uuid import uuid4

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from backend.app.core.dependencies import get_current_tenant, require_role
from backend.app.core.models import User, UserRole
from backend.app.schemas.jobs import JobQueuedResponse
from backend.app.services.campaign_service import CampaignService
from backend.app.tasks.replanning_tasks import run_weekly_replan_task

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["replanning"])

REPLAN_ROLES = [
    UserRole.CMO,
    UserRole.CAMPAIGN_MANAGER,
    UserRole.TENANT_ADMIN,
    UserRole.PLATFORM_ADMIN,
]


async def get_db() -> AsyncIOMotorDatabase:
    mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    mongo_db_name = os.getenv("MONGODB_DB", "ntm")
    client = AsyncIOMotorClient(mongo_url)
    return client[mongo_db_name]


@router.post("/campaigns/{campaign_id}/replan", response_model=JobQueuedResponse, status_code=202)
async def replan_campaign(
    campaign_id: str,
    _: User = Depends(require_role(REPLAN_ROLES)),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> JobQueuedResponse:
    svc = CampaignService(db)
    campaign = await svc.get(campaign_id, tenant_id)
    job_id = str(uuid4())
    run_weekly_replan_task.delay(campaign["mandate_id"])
    logger.info("Queued replan task", extra={"mandate_id": campaign["mandate_id"], "campaign_id": campaign_id})
    return JobQueuedResponse(job_id=job_id, campaign_id=campaign_id)
