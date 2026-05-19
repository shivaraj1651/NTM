"""FastAPI router for Campaign endpoints (TASK-012)."""

import logging
import os

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from backend.app.core.auth import current_user
from backend.app.core.dependencies import get_current_tenant
from backend.app.core.models import User
from backend.app.schemas.campaign import (
    CampaignCreateRequest,
    CampaignUpdateRequest,
    CampaignConfirmRequest,
    CampaignResponse,
)
from backend.app.services.campaign_service import CampaignService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["campaigns"])


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------

async def get_db() -> AsyncIOMotorDatabase:
    mongo_url = os.getenv("MONGO_DB_URL", "mongodb://localhost:27017")
    mongo_db_name = os.getenv("MONGO_DB_NAME", "ntm")
    client = AsyncIOMotorClient(mongo_url)
    return client[mongo_db_name]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/campaigns", response_model=CampaignResponse, status_code=201)
async def create_campaign(
    body: CampaignCreateRequest,
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CampaignResponse:
    svc = CampaignService(db)
    return await svc.create(body.mandate_id, tenant_id)


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse, status_code=200)
async def get_campaign(
    campaign_id: str,
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CampaignResponse:
    svc = CampaignService(db)
    return await svc.get(campaign_id, tenant_id)


@router.put("/campaigns/{campaign_id}", response_model=CampaignResponse, status_code=200)
async def update_campaign(
    campaign_id: str,
    body: CampaignUpdateRequest,
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CampaignResponse:
    svc = CampaignService(db)
    return await svc.update(campaign_id, tenant_id, body.model_dump(exclude_none=True))


@router.post("/campaigns/{campaign_id}/confirm", response_model=CampaignResponse, status_code=200)
async def confirm_campaign(
    campaign_id: str,
    body: CampaignConfirmRequest,
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CampaignResponse:
    svc = CampaignService(db)
    return await svc.confirm(campaign_id, body.selected_concept_id, tenant_id)


@router.get("/campaigns/{campaign_id}/activation-plan", response_model=CampaignResponse, status_code=200)
async def get_activation_plan(
    campaign_id: str,
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CampaignResponse:
    svc = CampaignService(db)
    return await svc.get_activation_plan(campaign_id, tenant_id)


@router.post("/campaigns/{campaign_id}/approve-budget", response_model=CampaignResponse, status_code=200)
async def propose_budget(
    campaign_id: str,
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CampaignResponse:
    svc = CampaignService(db)
    return await svc.propose_budget(campaign_id, tenant_id)


@router.post("/campaigns/{campaign_id}/confirm-budget", response_model=CampaignResponse, status_code=200)
async def confirm_budget(
    campaign_id: str,
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CampaignResponse:
    svc = CampaignService(db)
    return await svc.confirm_budget(campaign_id, tenant_id)
