"""
FastAPI router for mandate analysis endpoints.

Provides endpoints for:
1. POST /api/v1/mandates/{mandate_id}/analyze-competitors - Trigger Phase 1 + enqueue Phase 2
2. GET /api/v1/jobs/{job_id} - Poll for Phase 2 completion
"""

import logging
from typing import Dict, Any, Union
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.competitive_intel import competitive_intel_agent
from backend.app.core.dependencies import get_current_tenant, require_role
from backend.app.core.models import User, UserRole
from backend.app.db import get_db as _get_sql_db
from backend.app.schemas.competitive_intel import CIReportInitial, CIReport
from backend.app.schemas.mandate import CreateMandateRequest, UpdateMandateRequest
from backend.app.services.mandate_service import MandateService
from backend.app.tasks.competitive_intel_tasks import fetch_competitor_metrics
from backend.app.tasks.mandate_tasks import run_mandate_analysis
from backend.app.tasks.campaign_tasks import run_campaign_strategy

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["mandates"])

MANDATE_ROLES = [
    UserRole.BRAND_MANAGER,
    UserRole.CMO,
    UserRole.TENANT_ADMIN,
    UserRole.PLATFORM_ADMIN,
]


async def get_sql_db():
    """SQLAlchemy AsyncSession dependency (separate from MongoDB get_db above)."""
    async for session in _get_sql_db():
        yield session


async def get_db() -> AsyncIOMotorDatabase:
    """
    Dependency: Get MongoDB connection.

    In production, this would be injected from a global connection pool.
    """
    from motor.motor_asyncio import AsyncIOMotorClient
    import os

    mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    mongo_db_name = os.getenv("MONGODB_DB", "ntm")

    client = AsyncIOMotorClient(mongo_url)
    try:
        yield client[mongo_db_name]
    finally:
        client.close()


@router.post(
    "/mandates/{mandate_id}/analyze-competitors",
    response_model=CIReportInitial,
    status_code=200,
)
async def analyze_competitors(
    mandate_id: UUID,
    user: User = Depends(require_role(MANDATE_ROLES)),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CIReportInitial:
    """
    Trigger Phase 1 (competitor identification) + enqueue Phase 2 (metrics gathering).

    Endpoint: POST /api/v1/mandates/{mandate_id}/analyze-competitors

    Auth: JWT required (Bearer token)
    Path params:
        mandate_id: UUID of mandate to analyze

    Returns:
        CIReportInitial with job_id, mandate_id, competitors list, status='pending'

    Errors:
        404: Mandate not found or Client profile not found
        400: Competitor analysis failed (validation/LLM error)
    """
    mandate_id_str = str(mandate_id)

    # Fetch mandate from MongoDB
    mandates_collection = db["mandates"]
    mandate = await mandates_collection.find_one({
        "_id": mandate_id_str,
        "tenant_id": tenant_id,
    })

    if not mandate:
        logger.warning(
            f"Mandate not found: mandate_id={mandate_id_str}, tenant_id={tenant_id}"
        )
        raise HTTPException(status_code=404, detail="Mandate not found")

    # Fetch client profile from MongoDB
    clients_collection = db["clients"]
    client_id = mandate.get("client_id")

    if not client_id:
        logger.warning(
            f"Mandate missing client_id: mandate_id={mandate_id_str}"
        )
        raise HTTPException(status_code=404, detail="Mandate is missing client_id")

    client_profile = await clients_collection.find_one({
        "_id": client_id,
        "tenant_id": tenant_id,
    })

    if not client_profile:
        logger.warning(
            f"Client profile not found: client_id={client_id}, tenant_id={tenant_id}"
        )
        raise HTTPException(status_code=404, detail="Client profile not found")

    # Run Phase 1: Competitive Intelligence Agent (sync, <2s)
    try:
        logger.info(
            f"Starting Phase 1 for mandate_id={mandate_id_str}, tenant_id={tenant_id}"
        )

        # Convert mandate to dict if needed
        mandate_dict = dict(mandate) if hasattr(mandate, '__iter__') else mandate
        client_dict = dict(client_profile) if hasattr(client_profile, '__iter__') else client_profile

        # Remove MongoDB _id fields if present to avoid confusion
        mandate_dict.pop("_id", None)
        client_dict.pop("_id", None)

        # Call Phase 1 agent
        ci_report_initial = await competitive_intel_agent(
            mandate=mandate_dict,
            client_profile=client_dict,
            mandate_id=mandate_id_str,
            tenant_id=tenant_id,
        )

        logger.info(
            f"Phase 1 complete: job_id={ci_report_initial.job_id}, "
            f"competitors={len(ci_report_initial.competitors)}"
        )

    except ValueError as e:
        logger.error(f"Phase 1 validation error: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Competitor analysis failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in Phase 1: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Competitor analysis failed: {str(e)}"
        )

    # Save CIReportInitial to MongoDB ci_reports collection
    try:
        ci_reports_collection = db["ci_reports"]

        # Add tenant_id to the report before saving
        report_dict = ci_report_initial.model_dump(mode="json")
        report_dict["tenant_id"] = tenant_id

        await ci_reports_collection.insert_one(report_dict)
        logger.info(f"Saved CIReportInitial: job_id={ci_report_initial.job_id}")

    except Exception as e:
        logger.error(f"Failed to save CIReportInitial: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to save initial report"
        )

    # Enqueue Phase 2 Celery task (non-blocking)
    try:
        competitor_names = [c.name for c in ci_report_initial.competitors]

        logger.info(
            f"Enqueueing Phase 2 task: job_id={ci_report_initial.job_id}, "
            f"competitors={len(competitor_names)}"
        )

        fetch_competitor_metrics.delay(
            mandate_id=mandate_id_str,
            competitor_names=competitor_names,
            mandate_dict=mandate_dict,
            tenant_id=tenant_id,
            job_id=ci_report_initial.job_id,
        )

        logger.info(f"Phase 2 task enqueued: job_id={ci_report_initial.job_id}")

    except Exception as e:
        logger.error(f"Failed to enqueue Phase 2 task: {e}")
        # Log but don't fail - Phase 1 completed successfully
        # Client can poll job_id and see if Phase 2 completes later

    # Return CIReportInitial immediately
    return ci_report_initial


@router.get(
    "/jobs/{job_id}",
    response_model=Union[CIReportInitial, CIReport],
    status_code=200,
)
async def get_job_status(
    job_id: UUID,
    user: User = Depends(require_role(MANDATE_ROLES)),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Union[CIReportInitial, CIReport]:
    """
    Poll for Phase 2 completion.

    Endpoint: GET /api/v1/jobs/{job_id}

    Auth: JWT required (Bearer token)
    Path params:
        job_id: UUID from POST /analyze-competitors response

    Returns:
        CIReport if status='complete' (Phase 2 done)
        CIReportInitial if status='pending' (Phase 2 still running)

    Errors:
        404: Job not found
    """
    job_id_str = str(job_id)

    # Fetch from MongoDB ci_reports collection
    ci_reports_collection = db["ci_reports"]
    report = await ci_reports_collection.find_one({
        "job_id": job_id_str,
        "tenant_id": tenant_id,
    })

    if not report:
        logger.warning(
            f"Job not found: job_id={job_id_str}, tenant_id={tenant_id}"
        )
        raise HTTPException(status_code=404, detail="Job not found")

    # Remove MongoDB _id from response
    report.pop("_id", None)

    # Return appropriate schema based on status
    status = report.get("status", "pending")

    if status == "pending":
        logger.info(f"Job still pending: job_id={job_id_str}")
        return CIReportInitial(**report)
    else:
        # Complete, partial, or failed - return full CIReport
        logger.info(f"Job complete: job_id={job_id_str}, status={status}")
        return CIReport(**report)


# ---------------------------------------------------------------------------
# Mandate CRUD + lifecycle (SQLAlchemy / Postgres)
# ---------------------------------------------------------------------------

@router.post("/mandates", status_code=201)
async def create_mandate(
    body: CreateMandateRequest,
    user: User = Depends(require_role(MANDATE_ROLES)),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_sql_db),
) -> dict:
    svc = MandateService(db)
    result = await svc.create(body, user.id, tenant_id)
    run_mandate_analysis.delay(result["id"], tenant_id)
    return result


@router.get("/mandates/{mandate_id}", status_code=200)
async def get_mandate(
    mandate_id: str,
    user: User = Depends(require_role(MANDATE_ROLES)),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_sql_db),
) -> dict:
    svc = MandateService(db)
    return await svc.get(mandate_id, tenant_id)


@router.put("/mandates/{mandate_id}", status_code=200)
async def update_mandate(
    mandate_id: str,
    body: UpdateMandateRequest,
    user: User = Depends(require_role(MANDATE_ROLES)),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_sql_db),
) -> dict:
    svc = MandateService(db)
    return await svc.update(mandate_id, body, tenant_id)


@router.post("/mandates/{mandate_id}/confirm", status_code=200)
async def confirm_mandate(
    mandate_id: str,
    user: User = Depends(require_role(MANDATE_ROLES)),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_sql_db),
) -> dict:
    svc = MandateService(db)
    result = await svc.confirm(mandate_id, tenant_id)
    run_campaign_strategy.delay(mandate_id, tenant_id)
    return result


@router.get("/mandates/{mandate_id}/summary-card", status_code=200)
async def get_mandate_summary_card(
    mandate_id: str,
    user: User = Depends(require_role(MANDATE_ROLES)),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_sql_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    svc = MandateService(db)
    return await svc.get_summary_card(mandate_id, tenant_id, mongo_db)
