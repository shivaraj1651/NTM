"""Idempotent dev seed: roles, one tenant, one user per role."""
import asyncio
import uuid
from sqlalchemy import select
from backend.app.core.config import DEFAULT_RBAC_ROLES
from backend.app.core.models import User, Role, Tenant
from backend.app.core.auth_helpers import hash_password
from backend.app.db import get_session_local

TENANT_ID = "tenant-acme"
DEV_PASSWORD = "devpass123"
EMAIL_BY_ROLE = {
    "platform_admin": "admin@acme.test",
    "tenant_admin": "tenant@acme.test",
    "brand_manager": "brand@acme.test",
    "cmo": "cmo@acme.test",
    "creative_lead": "creative@acme.test",
    "campaign_manager": "campaign@acme.test",
    "viewer": "viewer@acme.test",
}


async def _get_or_create_role(session, name, perms):
    row = (await session.execute(select(Role).where(Role.name == name))).scalar_one_or_none()
    if row is None:
        row = Role(id=str(uuid.uuid4()), name=name, permissions=perms)
        session.add(row)
        await session.flush()
    return row


async def seed_all(session):
    tenant = (await session.execute(select(Tenant).where(Tenant.id == TENANT_ID))).scalar_one_or_none()
    if tenant is None:
        session.add(Tenant(id=TENANT_ID, name="Acme", is_active=True))
        await session.flush()
    for role_name, perms in DEFAULT_RBAC_ROLES.items():
        role = await _get_or_create_role(session, role_name, perms)
        email = EMAIL_BY_ROLE[role_name]
        existing = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if existing is None:
            session.add(User(
                id=str(uuid.uuid4()), email=email,
                hashed_password=hash_password(DEV_PASSWORD),
                tenant_id=TENANT_ID, role_id=role.id, is_active=True,
            ))
    await session.commit()


async def _main():
    factory = get_session_local()
    async with factory() as session:
        await seed_all(session)
    print("Seed complete: tenant=%s, users=%d" % (TENANT_ID, len(EMAIL_BY_ROLE)))


if __name__ == "__main__":
    asyncio.run(_main())
