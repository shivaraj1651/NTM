"""Pydantic schemas for Creatives resource endpoints (PRD Section 10)."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class CreativeResponse(BaseModel):
    id: str
    campaign_id: Optional[str] = None
    tenant_id: Optional[str] = None
    generation_id: Optional[str] = None
    platform: Optional[str] = None
    creative_type: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    validation_status: Optional[str] = None
    refinement_attempts: Optional[int] = None
    internal_approved_at: Optional[str] = None
    client_approved_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class CreativeListResponse(BaseModel):
    creatives: List[CreativeResponse]
    total: int


class RevisionRequest(BaseModel):
    comment: str
