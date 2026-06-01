"""Physical Activation Tracker router — M8 proof-of-execution logging."""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dependencies import get_current_tenant, require_role
from backend.app.core.models import User, UserRole
from backend.app.db import get_db
from backend.app.models.physical_activation_log import PhysicalActivationLog

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/activations", tags=["physical-activation"])

PHYSICAL_ROLES = [
    UserRole.CAMPAIGN_MANAGER,
    UserRole.TENANT_ADMIN,
    UserRole.PLATFORM_ADMIN,
]


# ── Schemas ───────────────────────────────────────────────────────────────────

class PhysicalLogCreate(BaseModel):
    campaign_id: str
    channel: str
    event_type: str = "proof_of_execution"
    actual_run_date: str | None = None
    actual_cost: float | None = None
    vendor_name: str | None = None
    grp_circulation: str | None = None
    proof_urls: list[str] = []
    notes: str | None = None


class PhysicalLogResponse(BaseModel):
    id: str
    tenant_id: str
    campaign_id: str
    activation_id: str | None
    event_type: str
    channel: str
    payload: dict
    logged_at: str
    created_at: str


def _to_response(log: PhysicalActivationLog) -> PhysicalLogResponse:
    return PhysicalLogResponse(
        id=log.id,
        tenant_id=log.tenant_id,
        campaign_id=log.campaign_id,
        activation_id=log.activation_id,
        event_type=log.event_type,
        channel=log.channel,
        payload=log.payload,
        logged_at=log.logged_at.isoformat() if log.logged_at else "",
        created_at=log.created_at.isoformat() if log.created_at else "",
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/{activation_id}/log-physical", response_model=PhysicalLogResponse, status_code=201)
async def log_physical_activation(
    activation_id: str,
    body: PhysicalLogCreate,
    user: User = Depends(require_role(PHYSICAL_ROLES)),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> PhysicalLogResponse:
    payload = {
        "actual_run_date": body.actual_run_date,
        "actual_cost": body.actual_cost,
        "vendor_name": body.vendor_name,
        "grp_circulation": body.grp_circulation,
        "proof_urls": body.proof_urls,
        "notes": body.notes,
        "logged_by": user.id,
    }
    log = PhysicalActivationLog(
        tenant_id=tenant_id,
        campaign_id=body.campaign_id,
        activation_id=activation_id,
        event_type=body.event_type,
        channel=body.channel,
        payload=payload,
        logged_at=datetime.now(UTC),
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return _to_response(log)


@router.get("/{activation_id}/physical-logs", response_model=list[PhysicalLogResponse])
async def list_physical_logs(
    activation_id: str,
    _: User = Depends(require_role(PHYSICAL_ROLES)),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> list[PhysicalLogResponse]:
    result = await db.execute(
        select(PhysicalActivationLog)
        .where(
            PhysicalActivationLog.activation_id == activation_id,
            PhysicalActivationLog.tenant_id == tenant_id,
        )
        .order_by(PhysicalActivationLog.logged_at.desc())
    )
    logs = result.scalars().all()
    return [_to_response(log) for log in logs]
