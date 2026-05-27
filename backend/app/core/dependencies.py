"""FastAPI dependency injection for tenant context and current user."""

from contextvars import ContextVar
from fastapi import Depends, HTTPException
from backend.app.core.auth import current_user
from backend.app.core.models import User, UserRole

# Context variable for async-safe tenant storage
tenant_context: ContextVar[str | None] = ContextVar('tenant_id', default=None)


async def get_current_tenant() -> str | None:
    """Inject tenant_id from context."""
    return tenant_context.get()


async def get_current_user_with_tenant(
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant)
) -> tuple[User, str]:
    """Inject both user and validated tenant."""
    return user, tenant_id


def require_role(allowed_roles: list[UserRole]):
    """
    FastAPI dependency factory for role-based access control.

    Usage:
        @router.get("/resource")
        async def endpoint(user: User = Depends(require_role([UserRole.CMO, UserRole.BRAND_MANAGER]))):
            ...

    Raises HTTPException(403) if the authenticated user's role is not in allowed_roles.
    allowed_roles values are compared against user.role.name (the Role.name column).
    """
    allowed_names = {r.value for r in allowed_roles}

    async def _dependency(user: User = Depends(current_user)) -> User:
        if user.role is None or user.role.name not in allowed_names:
            raise HTTPException(
                status_code=403,
                detail=f"Access restricted. Allowed roles: {', '.join(sorted(allowed_names))}",
            )
        return user

    return _dependency
