"""
SQLAlchemy models for User, Role, Tenant with multi-tenant relationships.

All models use string UUIDs as primary keys and include created_at timestamps.
Multi-tenant access is handled via the user_tenant_access junction table.
"""

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Table, JSON, func
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from enum import Enum

from backend.app.models.base import Base


class UserRole(str, Enum):
    PLATFORM_ADMIN = "platform_admin"
    TENANT_ADMIN = "tenant_admin"
    BRAND_MANAGER = "brand_manager"
    CMO = "cmo"
    CREATIVE_LEAD = "creative_lead"
    CAMPAIGN_MANAGER = "campaign_manager"
    VIEWER = "viewer"


class Role(Base):
    """
    Role model defining user permissions in NTM.

    Each user has exactly one role. Permissions are stored as a JSON array.
    Role names are unique and immutable after creation.
    """
    __tablename__ = "roles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, nullable=False, index=True)
    permissions = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class Tenant(Base):
    """
    Tenant model for multi-tenant isolation.

    A tenant is an organization/workspace. Users belong to tenants.
    is_active allows soft-delete without breaking foreign keys.
    """
    __tablename__ = "tenants"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    users = relationship("User", back_populates="tenant")


class User(Base):
    """
    User model for authentication and multi-tenant membership.

    Each user has:
    - email (unique, for login)
    - hashed_password (never plain text)
    - primary tenant (tenant_id, required)
    - single role (role_id, required)
    - is_active flag

    Multi-tenant access is controlled via user_tenant_access table.
    """
    __tablename__ = "user"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    role_id = Column(String, ForeignKey("roles.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    tenant = relationship("Tenant", back_populates="users")
    role = relationship("Role")


# Junction table for users accessing multiple tenants
user_tenant_access = Table(
    "user_tenant_access",
    Base.metadata,
    Column("user_id", String, ForeignKey("user.id"), primary_key=True),
    Column("tenant_id", String, ForeignKey("tenants.id"), primary_key=True),
    Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
)
