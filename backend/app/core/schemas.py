"""
Pydantic schemas for request/response validation.

Schemas correspond to SQLAlchemy models but provide additional validation,
field filtering, and transformation for API contracts.
"""

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import List, Optional


class RoleRead(BaseModel):
    """Role response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    permissions: List[str]


class TenantRead(BaseModel):
    """Tenant response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    is_active: bool


class UserCreate(BaseModel):
    """User creation request schema."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")


class UserRead(BaseModel):
    """User response schema (excludes password)."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    is_active: bool
    tenant_id: str
    role: RoleRead


class UserUpdate(BaseModel):
    """User update request schema (all fields optional)."""
    model_config = ConfigDict(from_attributes=True)

    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    is_active: Optional[bool] = None


class TokenResponse(BaseModel):
    """Token response schema."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
