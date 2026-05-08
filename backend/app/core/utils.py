"""Tenant and role utility functions."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.core.models import User, Role, Tenant, user_tenant_access

async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """Query user by email."""
    result = await session.execute(select(User).where(User.email == email))
    return result.scalars().first()

async def get_user_tenants(session: AsyncSession, user_id: str) -> list[str]:
    """Get all tenants user has access to (primary + secondary)."""
    user = await session.get(User, user_id)
    if not user:
        return []

    primary = [user.tenant_id]
    result = await session.execute(select(user_tenant_access.c.tenant_id).where(user_tenant_access.c.user_id == user_id))
    secondary = result.scalars().all()

    return primary + secondary

async def validate_user_role(session: AsyncSession, user_id: str, required_permission: str) -> bool:
    """Check if user's role has a specific permission."""
    user = await session.get(User, user_id)
    if not user:
        return False

    role = await session.get(Role, user.role_id)
    if not role:
        return False

    permissions = role.permissions
    return "*" in permissions or required_permission in permissions

async def get_tenant_by_id(session: AsyncSession, tenant_id: str) -> Tenant | None:
    """Lookup active tenant."""
    result = await session.execute(select(Tenant).where(Tenant.id == tenant_id, Tenant.is_active == True))
    return result.scalars().first()

async def user_has_tenant_access(session: AsyncSession, user_id: str, tenant_id: str) -> bool:
    """Verify user can access a specific tenant."""
    allowed = await get_user_tenants(session, user_id)
    return tenant_id in allowed
