"""FastAPI router — PRD Section 10 Activation resource endpoints.

GET  /api/v1/activations                          — list activations
GET  /api/v1/activations/{id}                     — get activation detail
GET  /api/v1/activations/{id}/performance         — get performance metrics
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dependencies import get_current_tenant, require_role
from backend.app.core.models import User, UserRole
from backend.app.db import get_db
from backend.app.models.activation import Activation
from backend.app.models.performance_metric import PerformanceMetric

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["activations"])

ACTIVATION_ROLES = [
    UserRole.CAMPAIGN_MANAGER,
    UserRole.BRAND_MANAGER,
    UserRole.CMO,
    UserRole.TENANT_ADMIN,
    UserRole.PLATFORM_ADMIN,
]


@router.get("/activations", status_code=200)
async def list_activations(
    campaign_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    _: User = Depends(require_role(ACTIVATION_ROLES)),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """GET /activations?campaign_id=&status= — list activations for tenant."""
    stmt = select(Activation).where(Activation.tenant_id == tenant_id)
    if campaign_id:
        stmt = stmt.where(Activation.campaign_id == campaign_id)
    if status:
        stmt = stmt.where(Activation.status == status)
    result = await db.execute(stmt)
    activations = result.scalars().all()
    return {"activations": [a.to_dict() for a in activations], "total": len(activations)}


@router.get("/activations/{activation_id}", status_code=200)
async def get_activation(
    activation_id: str,
    _: User = Depends(require_role(ACTIVATION_ROLES)),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """GET /activations/{id} — get single activation detail."""
    activation = await _get_activation(db, activation_id, tenant_id)
    return activation.to_dict()


@router.get("/activations/{activation_id}/performance", status_code=200)
async def get_activation_performance(
    activation_id: str,
    _: User = Depends(require_role(ACTIVATION_ROLES)),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """GET /activations/{id}/performance — performance metrics for an activation."""
    await _get_activation(db, activation_id, tenant_id)
    stmt = (
        select(PerformanceMetric)
        .where(
            PerformanceMetric.activation_id == activation_id,
            PerformanceMetric.tenant_id == tenant_id,
        )
        .order_by(PerformanceMetric.date.desc())
    )
    result = await db.execute(stmt)
    metrics = result.scalars().all()
    return {
        "activation_id": activation_id,
        "metrics": [m.to_dict() for m in metrics],
        "total": len(metrics),
    }


async def _get_activation(db: AsyncSession, activation_id: str, tenant_id: str) -> Activation:
    stmt = select(Activation).where(
        Activation.id == activation_id,
        Activation.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    activation = result.scalar_one_or_none()
    if activation is None:
        raise HTTPException(status_code=404, detail="Activation not found")
    return activation
