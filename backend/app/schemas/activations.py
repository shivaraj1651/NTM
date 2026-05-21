"""Pydantic schemas for Activation resource endpoints (PRD Section 10)."""

from typing import List, Optional
from pydantic import BaseModel


class ActivationResponse(BaseModel):
    id: str
    tenant_id: Optional[str] = None
    campaign_id: Optional[str] = None
    channel: Optional[str] = None
    sub_channel: Optional[str] = None
    audience_segment: Optional[str] = None
    budget_allocated: Optional[float] = None
    currency: Optional[str] = None
    platform_config: Optional[dict] = None
    status: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ActivationListResponse(BaseModel):
    activations: List[ActivationResponse]
    total: int
