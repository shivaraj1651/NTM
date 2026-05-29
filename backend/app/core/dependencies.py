"""FastAPI dependency injection for tenant context and current user."""
from contextvars import ContextVar
from fastapi import Depends, HTTPException, Request
from backend.app.core.auth import current_user
from backend.app.core.models import User, UserRole

tenant_context: ContextVar[str | None] = ContextVar('tenant_id', default=None)


async def get_current_tenant(request: Request) -> str | None:
    """Inject tenant_id resolved by the middleware (request.state), context fallback."""
    return getattr(request.state, "tenant_id", None) or tenant_context.get()


async def get_current_user_with_tenant(
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> tuple[User, str]:
    return user, tenant_id


def require_role(allowed_roles: list[UserRole]):
    allowed_names = {r.value for r in allowed_roles}

    async def _dependency(user: User = Depends(current_user)) -> User:
        if user.role is None or user.role.name not in allowed_names:
            raise HTTPException(
                status_code=403,
                detail=f"Access restricted. Allowed roles: {', '.join(sorted(allowed_names))}",
            )
        return user

    return _dependency
