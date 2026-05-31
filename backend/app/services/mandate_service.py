"""MandateService — CRUD and lifecycle for mandate records (SQLAlchemy/Postgres)."""

import logging
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.mandate import Mandate
from backend.app.schemas.mandate import CreateMandateRequest, UpdateMandateRequest

logger = logging.getLogger(__name__)


class MandateService:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def _get_or_404(self, mandate_id: str, tenant_id: str) -> Mandate:
        result = await self._db.execute(
            select(Mandate).where(
                Mandate.id == mandate_id,
                Mandate.tenant_id == tenant_id,
            )
        )
        mandate = result.scalar_one_or_none()
        if mandate is None:
            raise HTTPException(status_code=404, detail="Mandate not found")
        return mandate

    async def create(self, data: CreateMandateRequest, user_id: str, tenant_id: str) -> dict:
        mandate = Mandate(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            client_id=data.client_id,
            name=data.name,
            description=data.description,
            objective=data.objective,
            region=data.region,
            countries=data.countries,
            competitors=data.competitors,
            total_budget=data.total_budget,
            currency=data.currency,
            start_date=data.start_date,
            end_date=data.end_date,
            status="draft",
        )
        self._db.add(mandate)
        await self._db.commit()
        await self._db.refresh(mandate)
        return mandate.to_dict()

    async def list(self, tenant_id: str) -> list[dict]:
        result = await self._db.execute(
            select(Mandate).where(Mandate.tenant_id == tenant_id).order_by(Mandate.id)
        )
        return [m.to_dict() for m in result.scalars().all()]

    async def get(self, mandate_id: str, tenant_id: str) -> dict:
        mandate = await self._get_or_404(mandate_id, tenant_id)
        return mandate.to_dict()

    async def update(self, mandate_id: str, data: UpdateMandateRequest, tenant_id: str) -> dict:
        mandate = await self._get_or_404(mandate_id, tenant_id)
        if mandate.status != "draft":
            raise HTTPException(
                status_code=409,
                detail=f"Cannot update mandate in status '{mandate.status}'"
            )
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(mandate, field, value)
        await self._db.commit()
        await self._db.refresh(mandate)
        return mandate.to_dict()

    async def confirm(self, mandate_id: str, tenant_id: str) -> dict:
        mandate = await self._get_or_404(mandate_id, tenant_id)
        if mandate.status != "analyzed":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot confirm mandate in status '{mandate.status}'"
            )
        mandate.status = "confirmed"
        await self._db.commit()
        await self._db.refresh(mandate)
        return mandate.to_dict()

    async def get_summary_card(self, mandate_id: str, tenant_id: str, mongo_db) -> dict:
        """Return the flat mandate (the summary card the frontend renders).

        The mandate exists in SQL immediately after create, so this never 404s
        while the async AGT-01 analysis is still pending. When the analysis doc
        is ready it is merged in under ``analysis`` to enrich the card.
        """
        mandate = await self._get_or_404(mandate_id, tenant_id)
        card = mandate.to_dict()
        doc = await mongo_db["mandate_analyses"].find_one(
            {"mandate_id": mandate_id, "tenant_id": tenant_id}
        )
        if doc:
            card["analysis"] = doc.get("analysis")
            card["analyzed_at"] = doc.get("created_at")
        return card
