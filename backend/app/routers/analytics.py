import logging
import os
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from backend.app.core.auth import current_user
from backend.app.core.dependencies import get_current_tenant
from backend.app.core.models import User
from backend.app.schemas.jobs import JobQueuedResponse
from backend.app.services.campaign_service import CampaignService
from backend.app.tasks.analytics_tasks import run_daily_analytics_task

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["analytics"])


async def get_db() -> AsyncIOMotorDatabase:
    client = AsyncIOMotorClient(os.getenv("MONGO_DB_URL", "mongodb://localhost:27017"))
    return client[os.getenv("MONGO_DB_NAME", "ntm")]


@router.post("/campaigns/{campaign_id}/analytics/run", response_model=JobQueuedResponse, status_code=202)
async def run_analytics(
    campaign_id: str,
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> JobQueuedResponse:
    svc = CampaignService(db)
    campaign = await svc.get(campaign_id, tenant_id)
    job_id = str(uuid4())
    run_daily_analytics_task.delay(campaign["mandate_id"])
    logger.info("Queued analytics task", extra={"mandate_id": campaign["mandate_id"], "campaign_id": campaign_id})
    return JobQueuedResponse(job_id=job_id, campaign_id=campaign_id)


@router.get("/campaigns/{campaign_id}/analytics", status_code=200)
async def get_analytics(
    campaign_id: str,
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    svc = CampaignService(db)
    campaign = await svc.get(campaign_id, tenant_id)
    summary = await db["analytics_summaries"].find_one(
        {"mandate_id": campaign["mandate_id"], "tenant_id": tenant_id},
        sort=[("date", -1)],
    )
    if not summary:
        raise HTTPException(status_code=404, detail="No analytics result found. Run analytics first.")
    summary.pop("_id", None)
    return summary
