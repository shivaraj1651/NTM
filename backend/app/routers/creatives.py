"""FastAPI router — PRD Section 10 Creatives resource endpoints.

GET  /api/v1/creatives                            — list creatives
POST /api/v1/creatives/{id}/internal-approve      — internal team approves
POST /api/v1/creatives/{id}/client-approve        — client approves (AG-5)
POST /api/v1/creatives/{id}/request-revision      — request revision with comment
GET  /api/v1/creatives/{id}/download              — download asset URL
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.auth import current_user
from backend.app.core.dependencies import get_current_tenant, require_role
from backend.app.core.models import User, UserRole
from backend.app.db import get_db
from backend.app.models.creative import GeneratedCreative
from backend.app.schemas.creatives import RevisionRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["creatives"])

CREATIVE_ROLES = [
    UserRole.CREATIVE_LEAD,
    UserRole.BRAND_MANAGER,
    UserRole.CMO,
    UserRole.TENANT_ADMIN,
    UserRole.PLATFORM_ADMIN,
]


@router.get("/creatives", status_code=200)
async def list_creatives(
    activation_id: Optional[str] = Query(None),
    campaign_id: Optional[str] = Query(None),
    user: User = Depends(require_role(CREATIVE_ROLES)),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """GET /creatives?activation_id= — list creatives for an activation or campaign."""
    stmt = select(GeneratedCreative).where(GeneratedCreative.tenant_id == tenant_id)
    if campaign_id:
        stmt = stmt.where(GeneratedCreative.campaign_id == campaign_id)
    if activation_id:
        stmt = stmt.where(
            GeneratedCreative.content["activation_id"].as_string() == activation_id
        )
    result = await db.execute(stmt)
    creatives = result.scalars().all()
    return {"creatives": [c.to_dict() for c in creatives], "total": len(creatives)}


@router.post("/creatives/{creative_id}/internal-approve", status_code=200)
async def internal_approve_creative(
    creative_id: str,
    user: User = Depends(require_role(CREATIVE_ROLES)),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """POST /creatives/{id}/internal-approve — NTM internal team approves creative."""
    await _get_creative(db, creative_id, tenant_id)
    await db.execute(
        update(GeneratedCreative)
        .where(
            GeneratedCreative.id == creative_id,
            GeneratedCreative.tenant_id == tenant_id,
        )
        .values(
            validation_status="internal_approved",
            updated_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()
    logger.info("Creative internal-approved: %s", creative_id)
    return {"id": creative_id, "validation_status": "internal_approved"}


@router.post("/creatives/{creative_id}/client-approve", status_code=200)
async def client_approve_creative(
    creative_id: str,
    user: User = Depends(require_role(CREATIVE_ROLES)),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """POST /creatives/{id}/client-approve — client approves creative (Approval Gate 5)."""
    await _get_creative(db, creative_id, tenant_id)
    await db.execute(
        update(GeneratedCreative)
        .where(
            GeneratedCreative.id == creative_id,
            GeneratedCreative.tenant_id == tenant_id,
        )
        .values(
            validation_status="client_approved",
            updated_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()
    logger.info("Creative client-approved: %s", creative_id)
    return {"id": creative_id, "validation_status": "client_approved"}


@router.post("/creatives/{creative_id}/request-revision", status_code=200)
async def request_revision(
    creative_id: str,
    body: RevisionRequest,
    user: User = Depends(require_role(CREATIVE_ROLES)),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """POST /creatives/{id}/request-revision — request revision with comment."""
    creative = await _get_creative(db, creative_id, tenant_id)
    new_attempts = (creative.refinement_attempts or 0) + 1
    content = dict(creative.content or {})
    feedback_log = content.get("feedback_log", [])
    feedback_log.append({
        "comment": body.comment,
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "requested_by": str(user.id),
    })
    content["feedback_log"] = feedback_log
    await db.execute(
        update(GeneratedCreative)
        .where(
            GeneratedCreative.id == creative_id,
            GeneratedCreative.tenant_id == tenant_id,
        )
        .values(
            validation_status="revision_requested",
            refinement_attempts=new_attempts,
            content=content,
            updated_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()
    logger.info("Creative revision requested: %s (attempt %d)", creative_id, new_attempts)
    return {
        "id": creative_id,
        "validation_status": "revision_requested",
        "refinement_attempts": new_attempts,
        "comment": body.comment,
    }


@router.get("/creatives/{creative_id}/download", status_code=200)
async def download_creative(
    creative_id: str,
    user: User = Depends(require_role(CREATIVE_ROLES)),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """GET /creatives/{id}/download — return signed asset download URL."""
    creative = await _get_creative(db, creative_id, tenant_id)
    content = creative.content or {}
    asset_url = content.get("asset_url") or content.get("url") or content.get("image_url")
    if not asset_url:
        raise HTTPException(status_code=404, detail="No asset URL available for this creative")
    return {
        "id": creative_id,
        "asset_url": asset_url,
        "creative_type": creative.creative_type,
        "platform": creative.platform,
    }


async def _get_creative(db: AsyncSession, creative_id: str, tenant_id: str) -> GeneratedCreative:
    stmt = select(GeneratedCreative).where(
        GeneratedCreative.id == creative_id,
        GeneratedCreative.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    creative = result.scalar_one_or_none()
    if creative is None:
        raise HTTPException(status_code=404, detail="Creative not found")
    return creative
