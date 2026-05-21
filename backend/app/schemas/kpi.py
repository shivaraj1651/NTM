"""Pydantic schemas for KPI resource (PRD Section 10 / M10)."""

from typing import List, Optional
from pydantic import BaseModel


class KPICreate(BaseModel):
    mandate_id: str
    name: str
    category: str  # reach | engagement | conversion | revenue | brand_health | regional
    target_value: float
    unit: str
    measurement_method: Optional[str] = None


class KPIResponse(BaseModel):
    id: str
    campaign_id: Optional[str] = None
    mandate_id: Optional[str] = None
    tenant_id: Optional[str] = None
    channel_enum: Optional[str] = None
    audience_segment: Optional[str] = None
    kpi_name: Optional[str] = None
    target_value: Optional[float] = None
    threshold_unit: Optional[str] = None
    current_value: Optional[float] = None
    status: Optional[str] = None  # green | amber | red
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class KPIListResponse(BaseModel):
    kpis: List[KPIResponse]
    total: int
