"""Decode fastapi-users JWTs and load the user with role + allowed tenants."""
import jwt
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.core.config import settings
from backend.app.core.models import User, user_tenant_access

_AUDIENCE = "fastapi-users:auth"


def decode_user_id(token: str) -> str | None:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM], audience=_AUDIENCE,
        )
        return payload.get("sub")
    except Exception:
        return None


async def load_user_and_tenants(session, user_id: str):
    """Return (user, allowed_tenant_ids) or (None, []) if not found/inactive."""
    result = await session.execute(
        select(User).where(User.id == user_id).options(selectinload(User.role))
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        return None, []
    allowed = {user.tenant_id}
    rows = await session.execute(
        select(user_tenant_access.c.tenant_id).where(user_tenant_access.c.user_id == user_id)
    )
    allowed.update(r[0] for r in rows.all())
    return user, list(allowed)
