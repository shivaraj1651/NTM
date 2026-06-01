"""Pydantic schemas for Admin router — tenants, users, roles, audit logs."""


from pydantic import BaseModel, EmailStr


class TenantCreate(BaseModel):
    name: str


class TenantResponse(BaseModel):
    id: str
    name: str
    is_active: bool
    created_at: str

    model_config = {"from_attributes": True}


class TenantUpdate(BaseModel):
    is_active: bool


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
    role: str | None = None
    created_at: str

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    is_active: bool


class RoleUpdate(BaseModel):
    role_name: str


class RoleResponse(BaseModel):
    id: str
    name: str
    permissions: list[str]
    user_count: int


class AuditLogResponse(BaseModel):
    id: str
    tenant_id: str
    entity_type: str
    entity_id: str
    action: str
    actor_id: str
    notes: str | None
    status_before: str | None
    status_after: str | None
    created_at: str

    model_config = {"from_attributes": True}
