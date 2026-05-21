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


# ---------------------------------------------------------------------------
# PRD Section 10 — exact API surface aliases
# ---------------------------------------------------------------------------

@router.post("/campaigns/{campaign_id}/approve-concept", response_model=CampaignResponse, status_code=200)
async def approve_concept(
    campaign_id: str,
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CampaignResponse:
    """PRD alias: approve-concept → confirm (selects first available concept)."""
    svc = CampaignService(db)
    campaign = await svc.get(campaign_id, tenant_id)
    concepts = campaign.get("concepts", [])
    concept_id = concepts[0]["id"] if concepts else None
    return await svc.confirm(campaign_id, concept_id, tenant_id)


@router.post("/campaigns/{campaign_id}/approve-plan", response_model=CampaignResponse, status_code=200)
async def approve_plan(
    campaign_id: str,
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CampaignResponse:
    """PRD alias: approve-plan → approve-budget + confirm-budget in one call."""
    svc = CampaignService(db)
    await svc.propose_budget(campaign_id, tenant_id)
    return await svc.confirm_budget(campaign_id, tenant_id)


@router.get("/campaigns/{campaign_id}/deck", status_code=200)
async def get_campaign_deck(
    campaign_id: str,
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    """GET /campaigns/{id}/deck — campaign concept deck (PDF metadata + structured content)."""
    svc = CampaignService(db)
    campaign = await svc.get(campaign_id, tenant_id)
    concepts = campaign.get("concepts", [])
    concept = concepts[0] if concepts else {}
    return {
        "campaign_id": campaign_id,
        "mandate_id": campaign.get("mandate_id"),
        "deck_url": campaign.get("deck_url"),
        "sections": {
            "executive_summary": concept.get("theme", ""),
            "campaign_name_options": concept.get("name_options", []),
            "tagline_options": concept.get("tagline_options", []),
            "narrative": concept.get("narrative", ""),
            "channel_mix": concept.get("channel_mix_json", {}),
            "phase_plan": concept.get("phase_plan_json", {}),
            "tone_board": concept.get("tone_board", []),
            "visual_direction": concept.get("visual_direction", ""),
            "risk_flags": concept.get("risk_flags", []),
        },
        "generated_at": campaign.get("updated_at"),
    }
