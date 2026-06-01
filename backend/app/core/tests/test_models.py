import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.models import Role, Tenant, User


@pytest.mark.asyncio
async def test_role_model(async_session: AsyncSession):
    """Role model should store name and permissions"""
    role = Role(
        id=str(uuid.uuid4()),
        name="tenant_admin",
        permissions=["tenant.manage", "user.manage"]
    )
    async_session.add(role)
    await async_session.commit()

    result = await async_session.execute(
        select(Role).where(Role.name == "tenant_admin")
    )
    fetched = result.scalars().first()

    assert fetched is not None
    assert fetched.name == "tenant_admin"
    assert "tenant.manage" in fetched.permissions

@pytest.mark.asyncio
async def test_tenant_model(async_session: AsyncSession):
    """Tenant model should store name and is_active flag"""
    tenant = Tenant(
        id=str(uuid.uuid4()),
        name="Acme Corp",
        is_active=True
    )
    async_session.add(tenant)
    await async_session.commit()

    result = await async_session.execute(
        select(Tenant).where(Tenant.name == "Acme Corp")
    )
    fetched = result.scalars().first()

    assert fetched is not None
    assert fetched.name == "Acme Corp"
    assert fetched.is_active is True

@pytest.mark.asyncio
async def test_user_model(async_session: AsyncSession):
    """User model should store email, password, tenant, role, is_active"""
    # Create role and tenant first
    role = Role(id=str(uuid.uuid4()), name="viewer", permissions=["analytics.read"])
    tenant = Tenant(id=str(uuid.uuid4()), name="Test Tenant")

    async_session.add_all([role, tenant])
    await async_session.commit()

    # Create user
    user = User(
        id=str(uuid.uuid4()),
        email="user@example.com",
        hashed_password="$2b$12$...",
        is_active=True,
        tenant_id=tenant.id,
        role_id=role.id
    )
    async_session.add(user)
    await async_session.commit()

    result = await async_session.execute(
        select(User).where(User.email == "user@example.com")
    )
    fetched = result.scalars().first()

    assert fetched is not None
    assert fetched.email == "user@example.com"
    assert fetched.is_active is True
    assert fetched.tenant_id == tenant.id

@pytest.mark.asyncio
async def test_user_email_unique_constraint(async_session: AsyncSession):
    """User email should be unique"""
    from sqlalchemy.exc import IntegrityError

    role = Role(id=str(uuid.uuid4()), name="viewer", permissions=["analytics.read"])
    tenant = Tenant(id=str(uuid.uuid4()), name="Test Tenant")

    user1 = User(
        id=str(uuid.uuid4()),
        email="duplicate@example.com",
        hashed_password="$2b$12$...",
        tenant_id=tenant.id,
        role_id=role.id
    )
    user2 = User(
        id=str(uuid.uuid4()),
        email="duplicate@example.com",
        hashed_password="$2b$12$...",
        tenant_id=tenant.id,
        role_id=role.id
    )

    async_session.add_all([role, tenant, user1])
    await async_session.commit()

    async_session.add(user2)
    with pytest.raises(IntegrityError):
        await async_session.commit()

@pytest.mark.asyncio
async def test_role_name_unique_constraint(async_session: AsyncSession):
    """Role name should be unique"""
    from sqlalchemy.exc import IntegrityError

    role1 = Role(id=str(uuid.uuid4()), name="admin", permissions=["*"])
    role2 = Role(id=str(uuid.uuid4()), name="admin", permissions=["read"])

    async_session.add(role1)
    await async_session.commit()

    async_session.add(role2)
    with pytest.raises(IntegrityError):
        await async_session.commit()
