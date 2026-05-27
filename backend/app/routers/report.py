"""FastAPI router for Report endpoints (TASK-phase4)."""

import logging
import os
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dependencies import get_current_tenant, require_role
from backend.app.core.models import User, UserRole
from backend.app.db import get_db
from backend.app.schemas.jobs import JobQueuedResponse
from backend.app.services.campaign_service import CampaignService
from backend.app.services.report_service import ReportService
from backend.app.tasks.report_tasks import generate_daily_report_task

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["report"])

REPORT_ROLES = [
    UserRole.CMO,
    UserRole.TENANT_ADMIN,
    UserRole.PLATFORM_ADMIN,
]


async def get_mongo_db() -> AsyncIOMotorDatabase:
    client = AsyncIOMotorClient(os.getenv("MONGO_DB_URL", "mongodb://localhost:27017"))
    return client[os.getenv("MONGO_DB_NAME", "ntm")]


@router.post(
    "/campaigns/{campaign_id}/report/generate",
    response_model=JobQueuedResponse,
    status_code=202,
)
async def generate_report(
    campaign_id: str,
    user: User = Depends(require_role(REPORT_ROLES)),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> JobQueuedResponse:
    svc = CampaignService(db)
    campaign = await svc.get(campaign_id, tenant_id)
    job_id = str(uuid4())
    generate_daily_report_task.delay(campaign["mandate_id"], tenant_id)
    logger.info("Queued report task", extra={"mandate_id": campaign["mandate_id"]})
    return JobQueuedResponse(job_id=job_id, campaign_id=campaign_id)


@router.get("/campaigns/{campaign_id}/report", status_code=200)
async def get_report(
    campaign_id: str,
    user: User = Depends(require_role(REPORT_ROLES)),
    tenant_id: str = Depends(get_current_tenant),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
    sql_db: AsyncSession = Depends(get_db),
) -> dict:
    campaign_svc = CampaignService(mongo_db)
    campaign = await campaign_svc.get(campaign_id, tenant_id)
    report_svc = ReportService(sql_db)
    report = await report_svc.get_latest(
        mandate_id=campaign["mandate_id"],
        report_type="daily",
        tenant_id=tenant_id,
    )
    if report is None:
        raise HTTPException(status_code=404, detail="No report found. Run report generation first.")
    return {
        "mandate_id": report.mandate_id,
        "tenant_id": report.tenant_id,
        "report_type": report.report_type,
        "period_start": str(report.period_start),
        "period_end": str(report.period_end),
        "report_json": report.report_json,
    }
