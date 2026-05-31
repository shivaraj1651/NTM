"""FastAPI router for client onboarding.

POST /api/v1/clients — create a client org profile from the onboarding wizard.

The Client is the canonical relational record (SQL). Because the mandate
analysis and competitive-intelligence read paths look the client up in MongoDB
(``db["clients"]``), the create handler also upserts a mirror document into the
Mongo ``clients`` collection so the full onboarding -> mandate -> analysis flow
resolves the client.
"""

import json
import logging
import os
import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dependencies import get_current_tenant, require_role
from backend.app.core.models import User, UserRole
from backend.app.db import get_db as _get_sql_db
from backend.app.models.client import Client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["clients"])

# Same actors who own mandates may onboard clients (onboarding feeds mandate creation).
CLIENT_ROLES = [
    UserRole.BRAND_MANAGER,
    UserRole.CMO,
    UserRole.TENANT_ADMIN,
    UserRole.PLATFORM_ADMIN,
]


async def get_sql_db():
    """SQLAlchemy AsyncSession dependency."""
    async for session in _get_sql_db():
        yield session


async def get_mongo_db() -> AsyncIOMotorDatabase:
    """MongoDB connection dependency."""
    mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    mongo_db_name = os.getenv("MONGODB_DB", "ntm")
    client = AsyncIOMotorClient(mongo_url)
    try:
        yield client[mongo_db_name]
    finally:
        client.close()


def _parse_competitors(raw: str | None) -> list[str]:
    """Accept a JSON array string (sent by the onboarding wizard) or CSV fallback."""
    if not raw:
        return []
    try:
        value = json.loads(raw)
        if isinstance(value, list):
            return [str(item) for item in value]
    except (json.JSONDecodeError, TypeError):
        return [part.strip() for part in raw.split(",") if part.strip()]
    return []


@router.post("/clients", status_code=201)
async def create_client(
    org_name: str = Form(...),
    industry: str = Form(...),
    competitors: str | None = Form(None),
    logo: UploadFile | None = File(None),
    brand_guidelines: UploadFile | None = File(None),
    _: User = Depends(require_role(CLIENT_ROLES)),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_sql_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> dict:
    """Create a client profile (SQL canonical + Mongo mirror for the agent read paths)."""
    client_id = str(uuid.uuid4())
    competitor_list = _parse_competitors(competitors)
    # NOTE: binary upload to MinIO/S3 is a follow-up; store the supplied filename
    # as a lightweight reference for now (model fields are nullable).
    logo_url = logo.filename if logo is not None else None
    brand_guidelines_url = brand_guidelines.filename if brand_guidelines is not None else None

    client = Client(
        id=client_id,
        tenant_id=tenant_id,
        org_name=org_name,
        industry=industry,
        logo_url=logo_url,
        brand_guidelines_url=brand_guidelines_url,
        competitors=competitor_list,
    )
    db.add(client)
    await db.commit()
    await db.refresh(client)
    result = client.to_dict()

    # Dual-write mirror so db["clients"] readers (mandate.py, competitive_intel) resolve it.
    doc = {
        "_id": client_id,
        "tenant_id": tenant_id,
        "org_name": org_name,
        "industry": industry,
        "logo_url": logo_url,
        "brand_guidelines_url": brand_guidelines_url,
        "competitors": competitor_list,
    }
    try:
        await mongo_db["clients"].replace_one({"_id": client_id}, doc, upsert=True)
    except Exception as exc:  # pragma: no cover - mirror failure must not block onboarding
        logger.warning("Client Mongo mirror write failed for %s: %s", client_id, exc)

    return result
