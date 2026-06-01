from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.client import Client


@pytest.mark.asyncio
async def test_create_client(db_session: AsyncSession):
    tenant_id = str(uuid4())
    client = Client(
        tenant_id=tenant_id,
        org_name="Acme Corp",
        industry="Technology",
        logo_url="https://example.com/logo.png",
        brand_guidelines_url="https://example.com/brand.pdf",
        competitors=["CompetitorA", "CompetitorB"],
    )
    db_session.add(client)
    await db_session.commit()

    result = await db_session.execute(
        select(Client).where(Client.tenant_id == tenant_id)
    )
    fetched = result.scalar_one()

    assert fetched.org_name == "Acme Corp"
    assert fetched.industry == "Technology"
    assert fetched.competitors == ["CompetitorA", "CompetitorB"]
    assert fetched.created_at is not None
    assert fetched.updated_at is not None


@pytest.mark.asyncio
async def test_client_nullable_fields(db_session: AsyncSession):
    tenant_id = str(uuid4())
    client = Client(
        tenant_id=tenant_id,
        org_name="Minimal Corp",
        industry="Finance",
    )
    db_session.add(client)
    await db_session.commit()

    result = await db_session.execute(
        select(Client).where(Client.tenant_id == tenant_id)
    )
    fetched = result.scalar_one()

    assert fetched.logo_url is None
    assert fetched.brand_guidelines_url is None
    assert fetched.competitors == []


@pytest.mark.asyncio
async def test_client_to_dict(db_session: AsyncSession):
    tenant_id = str(uuid4())
    client = Client(
        tenant_id=tenant_id,
        org_name="Dict Corp",
        industry="Retail",
        competitors=["X", "Y"],
    )
    db_session.add(client)
    await db_session.commit()

    result = await db_session.execute(
        select(Client).where(Client.id == client.id)
    )
    fetched = result.scalar_one()
    d = fetched.to_dict()

    assert d["tenant_id"] == tenant_id
    assert d["org_name"] == "Dict Corp"
    assert d["industry"] == "Retail"
    assert d["competitors"] == ["X", "Y"]
    assert "created_at" in d
    assert "updated_at" in d


@pytest.mark.asyncio
async def test_client_tenant_isolation(db_session: AsyncSession):
    tenant_a = str(uuid4())
    tenant_b = str(uuid4())
    db_session.add(Client(tenant_id=tenant_a, org_name="Corp A", industry="Tech"))
    db_session.add(Client(tenant_id=tenant_b, org_name="Corp B", industry="Finance"))
    await db_session.commit()

    result = await db_session.execute(
        select(Client).where(Client.tenant_id == tenant_a)
    )
    clients = result.scalars().all()
    assert len(clients) == 1
    assert clients[0].org_name == "Corp A"
