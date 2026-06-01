"""Pydantic schemas for KPI resource (PRD Section 10 / M10)."""


from pydantic import BaseModel


class KPICreate(BaseModel):
    mandate_id: str
    name: str
    category: str  # reach | engagement | conversion | revenue | brand_health | regional
    target_value: float
    unit: str
    measurement_method: str | None = None


class KPIResponse(BaseModel):
    id: str
    campaign_id: str | None = None
    mandate_id: str | None = None
    tenant_id: str | None = None
    channel_enum: str | None = None
    audience_segment: str | None = None
    kpi_name: str | None = None
    target_value: float | None = None
    threshold_unit: str | None = None
    current_value: float | None = None
    status: str | None = None  # green | amber | red
    created_at: str | None = None
    updated_at: str | None = None


class KPIListResponse(BaseModel):
    kpis: list[KPIResponse]
    total: int
