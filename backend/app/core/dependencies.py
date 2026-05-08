"""FastAPI dependency injection for tenant context and current user."""

from contextvars import ContextVar
from fastapi import Depends
from backend.app.core.auth import current_user
from backend.app.core.models import User

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
