"""Pydantic schemas for campaign CRUD and lifecycle endpoints."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator


class CampaignStatusEnum(str, Enum):
    pending = "pending"
    concepts_ready = "concepts_ready"
    confirmed = "confirmed"
    planned = "planned"
    budget_proposed = "budget_proposed"
    approved = "approved"


class CampaignCreateRequest(BaseModel):
    mandate_id: str


class CampaignUpdateRequest(BaseModel):
    mandate_id: str | None = None
    selected_concept_id: str | None = None


class CampaignConfirmRequest(BaseModel):
    selected_concept_id: str


class CampaignResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    tenant_id: str
    mandate_id: str
    status: CampaignStatusEnum
    concepts: list[dict[str, Any]] = []
    selected_concept_id: str | None = None
    activation_plan: list[dict[str, Any]] | None = None
    budget_proposal: dict[str, Any] | None = None
    created_at: str | None = None
    updated_at: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _remap_mongo_id(cls, data: Any) -> Any:
        if isinstance(data, dict) and "_id" in data and "id" not in data:
            data = dict(data)
            data["id"] = str(data.pop("_id"))
        return data
