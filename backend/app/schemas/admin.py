"""Pydantic schemas for Admin router — tenants, users, roles, audit logs."""

from typing import Optional
from pydantic import BaseModel, EmailStr


class TenantCreate(BaseModel):
    name: str


class TenantResponse(BaseModel):
    id: str
    name: str
    is_active: bool
    created_at: str

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    tenant_id: str
    role_name: str = "viewer"


class UserResponse(BaseModel):
    id: str
    email: str
    tenant_id: str
    is_active: bool
    created_at: str

    model_config = {"from_attributes": True}


class RoleUpdate(BaseModel):
    role_name: str


class AuditLogResponse(BaseModel):
    id: str
    tenant_id: str
    entity_type: str
    entity_id: str
    action: str
    actor_id: str
    notes: Optional[str]
    status_before: Optional[str]
    status_after: Optional[str]
    created_at: str

    model_config = {"from_attributes": True}
