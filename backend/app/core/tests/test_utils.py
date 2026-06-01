import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.models import Role, Tenant, User, user_tenant_access
from backend.app.core.utils import (
    get_tenant_by_id,
    get_user_by_email,
    get_user_tenants,
    user_has_tenant_access,
    validate_user_role,
)


@pytest.mark.asyncio
async def test_get_user_by_email(async_session: AsyncSession):
    """get_user_by_email should return user by email"""
    role = Role(id=str(uuid.uuid4()), name="viewer", permissions=["analytics.read"])
    tenant = Tenant(id=str(uuid.uuid4()), name="Test Tenant")
    user = User(id=str(uuid.uuid4()), email="test@example.com", hashed_password="hash", tenant_id=tenant.id, role_id=role.id)
    async_session.add_all([role, tenant, user])
    await async_session.commit()

    found = await get_user_by_email(async_session, "test@example.com")
    assert found is not None
    assert found.email == "test@example.com"

@pytest.mark.asyncio
async def test_get_user_by_email_not_found(async_session: AsyncSession):
    """get_user_by_email should return None if not found"""
    found = await get_user_by_email(async_session, "notfound@example.com")
    assert found is None

@pytest.mark.asyncio
async def test_get_user_tenants_primary_only(async_session: AsyncSession):
    """get_user_tenants should return primary tenant"""
    role = Role(id=str(uuid.uuid4()), name="viewer", permissions=[])
    tenant = Tenant(id=str(uuid.uuid4()), name="Primary Tenant")
    user = User(id=str(uuid.uuid4()), email="user@example.com", hashed_password="hash", tenant_id=tenant.id, role_id=role.id)
    async_session.add_all([role, tenant, user])
    await async_session.commit()

    tenants = await get_user_tenants(async_session, user.id)
    assert tenant.id in tenants
    assert len(tenants) == 1

@pytest.mark.asyncio
async def test_get_user_tenants_with_secondary(async_session: AsyncSession):
    """get_user_tenants should return primary + secondary tenants"""
    role = Role(id=str(uuid.uuid4()), name="viewer", permissions=[])
    primary = Tenant(id=str(uuid.uuid4()), name="Primary")
    secondary = Tenant(id=str(uuid.uuid4()), name="Secondary")
    user = User(id=str(uuid.uuid4()), email="user@example.com", hashed_password="hash", tenant_id=primary.id, role_id=role.id)
    async_session.add_all([role, primary, secondary, user])
    await async_session.commit()

    stmt = user_tenant_access.insert().values(user_id=user.id, tenant_id=secondary.id)
    await async_session.execute(stmt)
    await async_session.commit()

    tenants = await get_user_tenants(async_session, user.id)
    assert primary.id in tenants
    assert secondary.id in tenants
    assert len(tenants) == 2

@pytest.mark.asyncio
async def test_validate_user_role_with_wildcard(async_session: AsyncSession):
    """validate_user_role should return True for wildcard permissions"""
    role = Role(id=str(uuid.uuid4()), name="admin", permissions=["*"])
    tenant = Tenant(id=str(uuid.uuid4()), name="Tenant")
    user = User(id=str(uuid.uuid4()), email="admin@example.com", hashed_password="hash", tenant_id=tenant.id, role_id=role.id)
    async_session.add_all([role, tenant, user])
    await async_session.commit()

    has_perm = await validate_user_role(async_session, user.id, "any.permission")
    assert has_perm is True

@pytest.mark.asyncio
async def test_validate_user_role_with_specific_permission(async_session: AsyncSession):
    """validate_user_role should return True for matching permission"""
    role = Role(id=str(uuid.uuid4()), name="tenant_admin", permissions=["tenant.manage", "user.manage"])
    tenant = Tenant(id=str(uuid.uuid4()), name="Tenant")
    user = User(id=str(uuid.uuid4()), email="admin@example.com", hashed_password="hash", tenant_id=tenant.id, role_id=role.id)
    async_session.add_all([role, tenant, user])
    await async_session.commit()

    has_perm = await validate_user_role(async_session, user.id, "tenant.manage")
    assert has_perm is True

@pytest.mark.asyncio
async def test_validate_user_role_missing_permission(async_session: AsyncSession):
    """validate_user_role should return False for missing permission"""
    role = Role(id=str(uuid.uuid4()), name="viewer", permissions=["analytics.read"])
    tenant = Tenant(id=str(uuid.uuid4()), name="Tenant")
    user = User(id=str(uuid.uuid4()), email="viewer@example.com", hashed_password="hash", tenant_id=tenant.id, role_id=role.id)
    async_session.add_all([role, tenant, user])
    await async_session.commit()

    has_perm = await validate_user_role(async_session, user.id, "tenant.manage")
    assert has_perm is False

@pytest.mark.asyncio
async def test_user_has_tenant_access_primary(async_session: AsyncSession):
    """user_has_tenant_access should return True for primary tenant"""
    role = Role(id=str(uuid.uuid4()), name="viewer", permissions=[])
    tenant = Tenant(id=str(uuid.uuid4()), name="Tenant")
    user = User(id=str(uuid.uuid4()), email="user@example.com", hashed_password="hash", tenant_id=tenant.id, role_id=role.id)
    async_session.add_all([role, tenant, user])
    await async_session.commit()

    has_access = await user_has_tenant_access(async_session, user.id, tenant.id)
    assert has_access is True

@pytest.mark.asyncio
async def test_user_has_tenant_access_denied(async_session: AsyncSession):
    """user_has_tenant_access should return False for unauthorized tenant"""
    role = Role(id=str(uuid.uuid4()), name="viewer", permissions=[])
    tenant1 = Tenant(id=str(uuid.uuid4()), name="Tenant 1")
    tenant2 = Tenant(id=str(uuid.uuid4()), name="Tenant 2")
    user = User(id=str(uuid.uuid4()), email="user@example.com", hashed_password="hash", tenant_id=tenant1.id, role_id=role.id)
    async_session.add_all([role, tenant1, tenant2, user])
    await async_session.commit()

    has_access = await user_has_tenant_access(async_session, user.id, tenant2.id)
    assert has_access is False

@pytest.mark.asyncio
async def test_get_tenant_by_id_active(async_session: AsyncSession):
    """get_tenant_by_id should return active tenant"""
    tenant = Tenant(id=str(uuid.uuid4()), name="Active Tenant", is_active=True)
    async_session.add(tenant)
    await async_session.commit()

    found = await get_tenant_by_id(async_session, tenant.id)
    assert found is not None
    assert found.name == "Active Tenant"

@pytest.mark.asyncio
async def test_get_tenant_by_id_inactive(async_session: AsyncSession):
    """get_tenant_by_id should not return inactive tenant"""
    tenant = Tenant(id=str(uuid.uuid4()), name="Inactive Tenant", is_active=False)
    async_session.add(tenant)
    await async_session.commit()

    found = await get_tenant_by_id(async_session, tenant.id)
    assert found is None
