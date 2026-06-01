"""Pydantic schemas for Creatives resource endpoints (PRD Section 10)."""

from typing import Any

from pydantic import BaseModel


class CreativeResponse(BaseModel):
    id: str
    campaign_id: str | None = None
    tenant_id: str | None = None
    generation_id: str | None = None
    platform: str | None = None
    creative_type: str | None = None
    content: dict[str, Any] | None = None
    validation_status: str | None = None
    refinement_attempts: int | None = None
    internal_approved_at: str | None = None
    client_approved_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class CreativeListResponse(BaseModel):
    creatives: list[CreativeResponse]
    total: int


class RevisionRequest(BaseModel):
    comment: str
