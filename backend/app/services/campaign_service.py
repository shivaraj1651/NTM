"""Campaign Service — business logic for the campaign lifecycle (TASK-012)."""

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select as _sa_select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from backend.app.models.mandate import Mandate

logger = logging.getLogger(__name__)

# Status ordering for guard comparisons
_STATUS_ORDER = [
    "pending",
    "concepts_ready",
    "confirmed",
    "planned",
    "budget_pending",
    "budget_proposed",
    "approved",
    "creative_generating",
    "creative_ready",
    "live",
]

_ASSET_KINDS = ("copy", "scripts", "images", "audio")


def _make_stub_creative_assets(campaign_id: str) -> dict:
    """Generate placeholder creative assets when real generation is unavailable."""
    return {
        "campaign_id": campaign_id,
        "stage": "internal_review",
        "copy": [
            {
                "asset_type": "headline",
                "variants": [
                    {"variant": "A", "content": "Bold Vision. Real Results.", "word_count": 4},
                    {"variant": "B", "content": "Your Brand, Amplified.", "word_count": 3},
                ],
                "approved": None,
                "revision_count": 0,
            },
            {
                "asset_type": "social_caption",
                "variants": [
                    {"variant": "A", "content": "Experience the difference. Join thousands already transforming their journey. #Innovation #Impact", "word_count": 15},
                    {"variant": "B", "content": "Ready to level up? We make it happen. Share your story. #Growth #Community", "word_count": 13},
                ],
                "approved": None,
                "revision_count": 0,
            },
            {
                "asset_type": "body_copy",
                "variants": [
                    {"variant": "A", "content": "In a world where attention is currency, your message needs to cut through. We craft campaigns that don't just reach audiences — they move them.", "word_count": 30},
                    {"variant": "B", "content": "Every brand has a story worth telling. We find yours, shape it, and deliver it to the people who matter most to your growth.", "word_count": 27},
                ],
                "approved": None,
                "revision_count": 0,
            },
        ],
        "scripts": [
            {
                "id": str(uuid.uuid4()),
                "format": "tvc_vo",
                "content": "Picture this. A world where your brand speaks directly to those who matter.\n\n[PAUSE]\n\nThat world exists. And we're here to build it with you.\n\n[BRAND]. Made for impact.",
                "duration_estimate": "30s",
                "approved": None,
                "revision_count": 0,
            },
            {
                "id": str(uuid.uuid4()),
                "format": "radio",
                "content": "Tired of blending in? We help businesses stand out. With data-driven strategies and creative excellence, we deliver campaigns that convert. Visit us today.",
                "duration_estimate": "30s",
                "approved": None,
                "revision_count": 0,
            },
        ],
        "images": [
            {
                "id": str(uuid.uuid4()),
                "format": "square",
                "url": "https://placehold.co/1024x1024/1a1a2e/ffffff?text=Square+Creative",
                "approved": None,
                "revision_count": 0,
            },
            {
                "id": str(uuid.uuid4()),
                "format": "landscape",
                "url": "https://placehold.co/1344x768/16213e/ffffff?text=Landscape+Creative",
                "approved": None,
                "revision_count": 0,
            },
            {
                "id": str(uuid.uuid4()),
                "format": "portrait",
                "url": "https://placehold.co/768x1344/0f3460/ffffff?text=Portrait+Creative",
                "approved": None,
                "revision_count": 0,
            },
        ],
        "audio": [
            {
                "id": str(uuid.uuid4()),
                "format": "radio",
                "voice_style": "warm",
                "url": "",
                "duration_seconds": 30,
                "approved": None,
                "revision_count": 0,
            },
        ],
    }


def _status_gte(current: str, minimum: str) -> bool:
    try:
        return _STATUS_ORDER.index(current) >= _STATUS_ORDER.index(minimum)
    except ValueError:
        return False


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CampaignService:
    """Orchestrates campaign lifecycle against MongoDB."""

    def __init__(self, db: Any):
        self._db = db

    @property
    def _campaigns(self):
        return self._db["campaigns"]

    @property
    def _mandates(self):
        return self._db["mandates"]

    @property
    def _ci_reports(self):
        return self._db["ci_reports"]

    # ------------------------------------------------------------------
    # create
    # ------------------------------------------------------------------

    @staticmethod
    async def _load_mandate_from_postgres(mandate_id: str, tenant_id: str) -> dict | None:
        """Load a mandate from Postgres (where MandateService stores them).

        Bridges the Postgres mandate store to this Mongo-based campaign service.
        Uses a fresh NullPool engine so it is safe inside any event loop (incl. Celery).
        """
        db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
        engine = create_async_engine(db_url, echo=False, poolclass=NullPool)
        try:
            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            async with factory() as session:
                result = await session.execute(
                    _sa_select(Mandate).where(
                        Mandate.id == mandate_id,
                        Mandate.tenant_id == tenant_id,
                    )
                )
                mandate = result.scalar_one_or_none()
                return mandate.to_dict() if mandate else None
        except Exception as exc:
            # No Postgres mandate reachable (missing table, no connection, etc.)
            # → treat as "not found" so the caller returns a clean 404.
            logger.warning("Postgres mandate lookup failed for %s: %s", mandate_id, exc)
            return None
        finally:
            await engine.dispose()

    async def create(self, mandate_id: str, tenant_id: str) -> dict:
        mandate = await self._mandates.find_one({"_id": mandate_id, "tenant_id": tenant_id})
        if not mandate:
            # Mandates are stored in Postgres (MandateService) — fall back to that store.
            mandate = await self._load_mandate_from_postgres(mandate_id, tenant_id)
        if not mandate:
            raise HTTPException(status_code=404, detail="Mandate not found")

        now = _utc_now()
        doc = {
            "_id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "mandate_id": mandate_id,
            "status": "pending",
            "concepts": [],
            "selected_concept_id": None,
            "activation_plan": None,
            "budget_proposal": None,
            "creative_assets": None,
            "kpi_configs": [],
            "created_at": now,
            "updated_at": now,
        }
        await self._campaigns.insert_one(doc)

        # Dispatch background concept generation (AGT-03)
        from backend.app.tasks.campaign_tasks import run_concept_generation
        try:
            run_concept_generation.delay(doc["_id"], tenant_id)
        except Exception as exc:
            logger.error("Failed to dispatch run_concept_generation for %s: %s", doc["_id"], exc)

        return doc

    # ------------------------------------------------------------------
    # get
    # ------------------------------------------------------------------

    async def list(self, tenant_id: str) -> list[dict]:
        cursor = self._campaigns.find({"tenant_id": tenant_id})
        return await cursor.to_list(length=None)

    async def get(self, campaign_id: str, tenant_id: str) -> dict:
        doc = await self._campaigns.find_one({"_id": campaign_id, "tenant_id": tenant_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return doc

    # ------------------------------------------------------------------
    # update
    # ------------------------------------------------------------------

    async def update(self, campaign_id: str, tenant_id: str, payload: dict) -> dict:
        await self.get(campaign_id, tenant_id)  # 404 guard
        allowed = {k: v for k, v in payload.items() if k in ("mandate_id", "selected_concept_id") and v is not None}
        allowed["updated_at"] = _utc_now()
        doc = await self._campaigns.find_one_and_update(
            {"_id": campaign_id, "tenant_id": tenant_id},
            {"$set": allowed},
            return_document=True,
        )
        return doc

    # ------------------------------------------------------------------
    # confirm
    # ------------------------------------------------------------------

    async def confirm(self, campaign_id: str, selected_concept_id: str, tenant_id: str) -> dict:
        doc = await self.get(campaign_id, tenant_id)

        if doc["status"] != "concepts_ready":
            raise HTTPException(status_code=409, detail=f"Cannot confirm from status '{doc['status']}'")

        concept_ids = {str(c.get("id", "")) for c in doc.get("concepts", [])}
        if selected_concept_id not in concept_ids:
            raise HTTPException(status_code=422, detail="selected_concept_id not found in concepts array")

        updated = await self._campaigns.find_one_and_update(
            {"_id": campaign_id, "tenant_id": tenant_id},
            {"$set": {
                "status": "confirmed",
                "selected_concept_id": selected_concept_id,
                "updated_at": _utc_now(),
            }},
            return_document=True,
        )

        # Dispatch background media planning (AGT-04)
        from backend.app.tasks.campaign_tasks import run_media_planning
        try:
            run_media_planning.delay(campaign_id, tenant_id)
        except Exception as exc:
            logger.error("Failed to dispatch run_media_planning for %s: %s", campaign_id, exc)

        return updated

    # ------------------------------------------------------------------
    # get_activation_plan
    # ------------------------------------------------------------------

    async def get_activation_plan(self, campaign_id: str, tenant_id: str) -> dict:
        return await self.get(campaign_id, tenant_id)

    # ------------------------------------------------------------------
    # propose_budget
    # ------------------------------------------------------------------

    async def propose_budget(self, campaign_id: str, tenant_id: str) -> dict:
        doc = await self.get(campaign_id, tenant_id)

        if doc["status"] != "planned":
            raise HTTPException(status_code=409, detail=f"Cannot propose budget from status '{doc['status']}'")

        updated = await self._campaigns.find_one_and_update(
            {"_id": campaign_id, "tenant_id": tenant_id},
            {"$set": {
                "status": "budget_pending",
                "updated_at": _utc_now(),
            }},
            return_document=True,
        )

        # Dispatch background budget optimization (AGT-05)
        from backend.app.tasks.campaign_tasks import run_budget_optimization
        try:
            run_budget_optimization.delay(campaign_id, tenant_id)
        except Exception as exc:
            logger.error("Failed to dispatch run_budget_optimization for %s: %s", campaign_id, exc)

        return updated

    # ------------------------------------------------------------------
    # confirm_budget
    # ------------------------------------------------------------------

    async def confirm_budget(self, campaign_id: str, tenant_id: str) -> dict:
        doc = await self.get(campaign_id, tenant_id)

        if doc["status"] not in ("budget_proposed", "budget_pending"):
            raise HTTPException(status_code=409, detail=f"Cannot confirm budget from status '{doc['status']}'")

        updated = await self._campaigns.find_one_and_update(
            {"_id": campaign_id, "tenant_id": tenant_id},
            {"$set": {"status": "approved", "updated_at": _utc_now()}},
            return_document=True,
        )
        return updated

    # ------------------------------------------------------------------
    # generate_creatives
    # ------------------------------------------------------------------

    async def generate_creatives(self, campaign_id: str, tenant_id: str) -> dict:
        doc = await self.get(campaign_id, tenant_id)

        if doc["status"] != "approved":
            raise HTTPException(status_code=409, detail=f"Cannot generate creatives from status '{doc['status']}'")

        updated = await self._campaigns.find_one_and_update(
            {"_id": campaign_id, "tenant_id": tenant_id},
            {"$set": {"status": "creative_generating", "updated_at": _utc_now()}},
            return_document=True,
        )
        from backend.app.tasks.campaign_tasks import run_creative_generation
        try:
            run_creative_generation.delay(campaign_id, tenant_id)
        except Exception as exc:
            logger.warning("creative generation task dispatch failed: %s", exc)
        return updated

    # ------------------------------------------------------------------
    # approve_creative_asset
    # ------------------------------------------------------------------

    async def approve_creative_asset(
        self,
        campaign_id: str,
        tenant_id: str,
        asset_kind: str,
        asset_id: str,
        approved: bool,
    ) -> dict:
        if asset_kind not in _ASSET_KINDS:
            raise HTTPException(status_code=422, detail=f"Invalid asset kind '{asset_kind}'. Must be one of: {_ASSET_KINDS}")

        doc = await self.get(campaign_id, tenant_id)
        if doc.get("status") not in ("creative_ready", "creative_generating"):
            raise HTTPException(status_code=409, detail="Campaign has no creative assets to approve")

        # copy assets are keyed by asset_type; all others by id
        match_field = "asset_type" if asset_kind == "copy" else "id"

        await self._campaigns.update_one(
            {"_id": campaign_id, "tenant_id": tenant_id},
            {
                "$set": {
                    f"creative_assets.{asset_kind}.$[elem].approved": approved,
                    "updated_at": _utc_now(),
                }
            },
            array_filters=[{f"elem.{match_field}": asset_id}],
        )
        return await self.get(campaign_id, tenant_id)

    # ------------------------------------------------------------------
    # regenerate_creative_asset
    # ------------------------------------------------------------------

    async def regenerate_creative_asset(
        self,
        campaign_id: str,
        tenant_id: str,
        asset_kind: str,
        asset_id: str,
    ) -> dict:
        if asset_kind not in _ASSET_KINDS:
            raise HTTPException(status_code=422, detail=f"Invalid asset kind '{asset_kind}'. Must be one of: {_ASSET_KINDS}")

        doc = await self.get(campaign_id, tenant_id)
        if doc.get("status") != "creative_ready":
            raise HTTPException(status_code=409, detail="Campaign has no creative assets to regenerate")

        match_field = "asset_type" if asset_kind == "copy" else "id"

        await self._campaigns.update_one(
            {"_id": campaign_id, "tenant_id": tenant_id},
            {
                "$set": {
                    f"creative_assets.{asset_kind}.$[elem].approved": None,
                    "updated_at": _utc_now(),
                },
                "$inc": {f"creative_assets.{asset_kind}.$[elem].revision_count": 1},
            },
            array_filters=[{f"elem.{match_field}": asset_id}],
        )
        return await self.get(campaign_id, tenant_id)

    # ------------------------------------------------------------------
    # go_live
    # ------------------------------------------------------------------

    async def go_live(self, campaign_id: str, tenant_id: str) -> dict:
        doc = await self.get(campaign_id, tenant_id)

        if doc["status"] != "creative_ready":
            raise HTTPException(status_code=409, detail=f"Cannot go live from status '{doc['status']}'")

        updated = await self._campaigns.find_one_and_update(
            {"_id": campaign_id, "tenant_id": tenant_id},
            {"$set": {"status": "live", "updated_at": _utc_now()}},
            return_document=True,
        )
        return updated
