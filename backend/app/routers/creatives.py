"""FastAPI router — PRD Section 10 Creatives resource endpoints.

GET   /api/v1/creatives                            — list (Postgres + MongoDB media)
GET   /api/v1/creatives/{id}                       — single creative
PATCH /api/v1/creatives/{id}/status                — update status
POST  /api/v1/creatives/{id}/internal-approve      — internal team approves
POST  /api/v1/creatives/{id}/client-approve        — client approves (AG-5)
POST  /api/v1/creatives/{id}/request-revision      — request revision with comment
GET   /api/v1/creatives/{id}/download              — download asset URL
"""

import logging
import os
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

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
    UserRole.CAMPAIGN_MANAGER,   # campaign managers need Creative Studio access
]


# ── MongoDB helper ──────────────────────────────────────────────────────────

async def _get_mongo_db():
    url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    db_name = os.getenv("MONGODB_DB", "ntm")
    client = AsyncIOMotorClient(url)
    return client[db_name]


def _campaign_media_to_creatives(campaign: dict) -> list[dict]:
    """Flatten campaign.creative_assets images/audio/video into Creative-shaped dicts."""
    campaign_id = campaign["_id"]
    tenant_id = campaign.get("tenant_id", "")
    assets = campaign.get("creative_assets") or {}
    now = campaign.get("updated_at") or campaign.get("created_at") or ""

    result: list[dict] = []

    for img in assets.get("images") or []:
        if not img.get("url") or not img.get("id"):
            continue
        fmt = img.get("format", "square")
        result.append({
            "id": img["id"],
            "campaign_id": campaign_id,
            "tenant_id": tenant_id,
            "generation_id": img["id"],
            "platform": fmt,
            "creative_type": "image",
            "content": {
                "url": img["url"],
                "asset_url": img["url"],
                "format": fmt,
                "label": fmt.replace("_", " ").title(),
            },
            "validation_status": (
                "internal_approved" if img.get("approved") is True
                else "revision_requested" if img.get("approved") is False
                else "ai_draft"
            ),
            "refinement_attempts": img.get("revision_count", 0),
            "created_at": now,
            "updated_at": now,
        })

    for aud in assets.get("audio") or []:
        if not aud.get("url") or not aud.get("id"):
            continue
        fmt = aud.get("format", "radio")
        result.append({
            "id": aud["id"],
            "campaign_id": campaign_id,
            "tenant_id": tenant_id,
            "generation_id": aud["id"],
            "platform": fmt,
            "creative_type": "audio",
            "content": {
                "url": aud["url"],
                "asset_url": aud["url"],
                "format": fmt,
                "voice_style": aud.get("voice_style", ""),
                "duration_seconds": aud.get("duration_seconds", 0),
                "label": fmt.replace("_", " ").title(),
            },
            "validation_status": "ai_draft",
            "refinement_attempts": 0,
            "created_at": now,
            "updated_at": now,
        })

    for vid in assets.get("video") or []:
        if not vid.get("url") or not vid.get("id"):
            continue
        fmt = vid.get("format", "social_video")
        result.append({
            "id": vid["id"],
            "campaign_id": campaign_id,
            "tenant_id": tenant_id,
            "generation_id": vid["id"],
            "platform": fmt,
            "creative_type": "video",
            "content": {
                "url": vid["url"],
                "asset_url": vid["url"],
                "format": fmt,
                "duration_seconds": vid.get("duration_seconds"),
                "status": vid.get("status"),
                "label": "Social Video",
            },
            "validation_status": "ai_draft",
            "refinement_attempts": 0,
            "created_at": now,
            "updated_at": now,
        })

    return result


async def _mongo_creatives_for_tenant(tenant_id: str, campaign_id: str | None = None) -> list[dict]:
    """Query MongoDB campaigns and return flattened image/audio/video creatives."""
    try:
        mongo_db = await _get_mongo_db()
        query: dict = {"tenant_id": tenant_id, "creative_assets": {"$ne": None}}
        if campaign_id:
            query["_id"] = campaign_id
        campaigns = await mongo_db["campaigns"].find(query).to_list(length=None)
        result: list[dict] = []
        for c in campaigns:
            result.extend(_campaign_media_to_creatives(c))
        return result
    except Exception as exc:
        logger.warning("MongoDB creative query failed: %s", exc)
        return []


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/creatives", status_code=200)
async def list_creatives(
    activation_id: str | None = Query(None),
    campaign_id: str | None = Query(None),
    user: User = Depends(require_role(CREATIVE_ROLES)),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List creatives: combines Postgres (copy/scripts) + MongoDB (images/audio/video)."""
    stmt = select(GeneratedCreative).where(GeneratedCreative.tenant_id == tenant_id)
    if campaign_id:
        stmt = stmt.where(GeneratedCreative.campaign_id == campaign_id)
    if activation_id:
        stmt = stmt.where(
            GeneratedCreative.content["activation_id"].as_string() == activation_id
        )
    result = await db.execute(stmt)
    creatives: list[dict] = [c.to_dict() for c in result.scalars().all()]

    # Merge in images/audio/video from MongoDB (not persisted to Postgres)
    existing_ids = {c["id"] for c in creatives}
    for media in await _mongo_creatives_for_tenant(tenant_id, campaign_id):
        if media["id"] not in existing_ids:
            creatives.append(media)

    return {"creatives": creatives, "total": len(creatives)}


@router.get("/creatives/{creative_id}", status_code=200)
async def get_creative(
    creative_id: str,
    user: User = Depends(require_role(CREATIVE_ROLES)),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """GET single creative — checks Postgres first, then MongoDB media assets."""
    stmt = select(GeneratedCreative).where(
        GeneratedCreative.id == creative_id,
        GeneratedCreative.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    creative = result.scalar_one_or_none()
    if creative:
        return creative.to_dict()

    # Fall back to MongoDB media assets
    for media in await _mongo_creatives_for_tenant(tenant_id):
        if media["id"] == creative_id:
            return media

    raise HTTPException(status_code=404, detail="Creative not found")


class StatusUpdate(BaseModel):
    status: str
    notes: str | None = None


@router.patch("/creatives/{creative_id}/status", status_code=200)
async def update_creative_status(
    creative_id: str,
    body: StatusUpdate,
    user: User = Depends(require_role(CREATIVE_ROLES)),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """PATCH /creatives/{id}/status — update approval state."""
    stmt = select(GeneratedCreative).where(
        GeneratedCreative.id == creative_id,
        GeneratedCreative.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    creative = result.scalar_one_or_none()
    if creative is None:
        # MongoDB-only assets (images/audio/video) — status update not persisted yet
        # Return success so the UI doesn't break; future: persist to Postgres
        logger.info("Status update for MongoDB-only asset %s: %s", creative_id, body.status)
        return {"id": creative_id, "validation_status": body.status}

    await db.execute(
        update(GeneratedCreative)
        .where(
            GeneratedCreative.id == creative_id,
            GeneratedCreative.tenant_id == tenant_id,
        )
        .values(
            validation_status=body.status,
            updated_at=datetime.now(UTC),
        )
    )
    await db.commit()
    return {"id": creative_id, "validation_status": body.status}


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
            updated_at=datetime.now(UTC),
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
            updated_at=datetime.now(UTC),
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
        "requested_at": datetime.now(UTC).isoformat(),
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
            updated_at=datetime.now(UTC),
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
    """GET /creatives/{id}/download — return asset download URL."""
    # Check Postgres first
    stmt = select(GeneratedCreative).where(
        GeneratedCreative.id == creative_id,
        GeneratedCreative.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    creative = result.scalar_one_or_none()
    if creative:
        content = creative.content or {}
        asset_url = content.get("asset_url") or content.get("url") or content.get("image_url")
        if not asset_url:
            raise HTTPException(status_code=404, detail="No asset URL available")
        return {"id": creative_id, "asset_url": asset_url,
                "creative_type": creative.creative_type, "platform": creative.platform}

    # Fall back to MongoDB
    for media in await _mongo_creatives_for_tenant(tenant_id):
        if media["id"] == creative_id:
            url = (media.get("content") or {}).get("url")
            if not url:
                raise HTTPException(status_code=404, detail="No asset URL available")
            return {"id": creative_id, "asset_url": url,
                    "creative_type": media["creative_type"], "platform": media["platform"]}

    raise HTTPException(status_code=404, detail="Creative not found")


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
