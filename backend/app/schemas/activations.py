"""Pydantic schemas for Activation resource endpoints (PRD Section 10)."""


from pydantic import BaseModel


class ActivationResponse(BaseModel):
    id: str
    tenant_id: str | None = None
    campaign_id: str | None = None
    channel: str | None = None
    sub_channel: str | None = None
    audience_segment: str | None = None
    budget_allocated: float | None = None
    currency: str | None = None
    platform_config: dict | None = None
    status: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ActivationListResponse(BaseModel):
    activations: list[ActivationResponse]
    total: int
