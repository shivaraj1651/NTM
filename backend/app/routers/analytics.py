import logging
import os
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.auth import current_user
from backend.app.core.dependencies import get_current_tenant
from backend.app.core.models import User
from backend.app.db import get_db
from backend.app.models.kpi import KPI
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


# ---------------------------------------------------------------------------
# PRD Section 10 — mandate-scoped analytics API surface
# ---------------------------------------------------------------------------

@router.get("/analytics/dashboard", status_code=200)
async def analytics_dashboard(
    mandate_id: str = Query(...),
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    mongo: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    """GET /analytics/dashboard?mandate_id= — unified campaign dashboard data."""
    summary = await mongo["analytics_summaries"].find_one(
        {"mandate_id": mandate_id, "tenant_id": tenant_id},
        sort=[("date", -1)],
    )
    if summary:
        summary.pop("_id", None)
    return {
        "mandate_id": mandate_id,
        "summary": summary or {},
    }


@router.get("/analytics/channel-performance", status_code=200)
async def channel_performance(
    mandate_id: str = Query(...),
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    mongo: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    """GET /analytics/channel-performance?mandate_id= — per-channel breakdown."""
    summary = await mongo["analytics_summaries"].find_one(
        {"mandate_id": mandate_id, "tenant_id": tenant_id},
        sort=[("date", -1)],
    )
    channel_data = {}
    if summary:
        channel_data = summary.get("summary_by_channel", {})
    return {"mandate_id": mandate_id, "channels": channel_data}


@router.get("/analytics/kpi-status", status_code=200)
async def kpi_status(
    mandate_id: Optional[str] = Query(None),
    campaign_id: Optional[str] = Query(None),
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    sql_db: AsyncSession = Depends(get_db),
) -> dict:
    """GET /analytics/kpi-status?mandate_id= — KPI achievement status."""
    stmt = select(KPI).where(KPI.tenant_id == tenant_id)
    if campaign_id:
        stmt = stmt.where(KPI.campaign_id == campaign_id)
    result = await sql_db.execute(stmt)
    kpis = result.scalars().all()
    kpi_list = [k.to_dict() for k in kpis]
    red = [k for k in kpi_list if k.get("status") == "red"]
    amber = [k for k in kpi_list if k.get("status") == "amber"]
    green = [k for k in kpi_list if k.get("status") == "green"]
    return {
        "mandate_id": mandate_id,
        "campaign_id": campaign_id,
        "kpis": kpi_list,
        "summary": {"total": len(kpi_list), "red": len(red), "amber": len(amber), "green": len(green)},
    }


@router.get("/analytics/report", status_code=200)
async def analytics_report(
    mandate_id: str = Query(...),
    week: Optional[int] = Query(None),
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    mongo: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    """GET /analytics/report?mandate_id=&week= — weekly intelligence report."""
    query: dict = {"mandate_id": mandate_id, "tenant_id": tenant_id}
    if week is not None:
        query["week"] = week
    report = await mongo["reports"].find_one(query, sort=[("generated_at", -1)])
    if not report:
        raise HTTPException(status_code=404, detail="No report found for this mandate.")
    report.pop("_id", None)
    return report


@router.post("/analytics/replan/approve/{recommendation_id}", status_code=200)
async def approve_replan_recommendation(
    recommendation_id: str,
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    mongo: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    """POST /analytics/replan/approve/{id} — campaign manager approves a replan recommendation."""
    result = await mongo["replan_recommendations"].find_one_and_update(
        {"id": recommendation_id, "tenant_id": tenant_id},
        {"$set": {"status": "approved", "approved_by": str(user.id)}},
        return_document=True,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    result.pop("_id", None)
    return {"recommendation_id": recommendation_id, "status": "approved"}
