"""Pydantic schemas for mandate CRUD and lifecycle endpoints."""

from datetime import date, datetime

from pydantic import BaseModel


class CreateMandateRequest(BaseModel):
    name: str
    client_id: str
    objective: str
    region: str
    total_budget: float
    currency: str
    start_date: date
    end_date: date
    description: str | None = None
    countries: list[str] = []
    competitors: list[str] = []


class UpdateMandateRequest(BaseModel):
    name: str | None = None
    client_id: str | None = None
    objective: str | None = None
    region: str | None = None
    total_budget: float | None = None
    currency: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None
    countries: list[str] | None = None
    competitors: list[str] | None = None


class MandateResponse(BaseModel):
    id: str
    tenant_id: str
    client_id: str
    name: str
    status: str
    objective: str
    region: str
    total_budget: float
    currency: str
    start_date: date | None
    end_date: date | None
    description: str | None
    countries: list[str]
    competitors: list[str]
    created_at: datetime | None
    updated_at: datetime | None
