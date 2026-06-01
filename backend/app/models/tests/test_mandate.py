from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.mandate import Mandate


@pytest.mark.asyncio
async def test_create_mandate(db_session: AsyncSession):
    tenant_id = str(uuid4())
    mandate = Mandate(
        tenant_id=tenant_id,
        client_id=str(uuid4()),
        name="Q3 Brand Awareness",
        objective="awareness",
        region="APAC",
        countries=["India", "Singapore"],
        competitors=["BrandX", "BrandY"],
        total_budget=500000.0,
        currency="USD",
        start_date=date(2025, 7, 1),
        end_date=date(2025, 9, 30),
    )
    db_session.add(mandate)
    await db_session.commit()

    result = await db_session.execute(
        select(Mandate).where(Mandate.tenant_id == tenant_id)
    )
    fetched = result.scalar_one()

    assert fetched.name == "Q3 Brand Awareness"
    assert fetched.objective == "awareness"
    assert fetched.countries == ["India", "Singapore"]
    assert fetched.competitors == ["BrandX", "BrandY"]
    assert fetched.total_budget == 500000.0
    assert fetched.status == "draft"
    assert fetched.description is None
    assert fetched.created_at is not None
    assert fetched.updated_at is not None


@pytest.mark.asyncio
async def test_mandate_defaults(db_session: AsyncSession):
    tenant_id = str(uuid4())
    mandate = Mandate(
        tenant_id=tenant_id,
        client_id=str(uuid4()),
        name="Minimal Mandate",
        objective="conversion",
        region="EMEA",
        countries=["UK"],
        total_budget=100000.0,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 6, 30),
    )
    db_session.add(mandate)
    await db_session.commit()

    result = await db_session.execute(
        select(Mandate).where(Mandate.tenant_id == tenant_id)
    )
    fetched = result.scalar_one()

    assert fetched.status == "draft"
    assert fetched.currency == "USD"
    assert fetched.competitors == []
    assert fetched.description is None


@pytest.mark.asyncio
async def test_mandate_to_dict(db_session: AsyncSession):
    tenant_id = str(uuid4())
    mandate = Mandate(
        tenant_id=tenant_id,
        client_id=str(uuid4()),
        name="Dict Mandate",
        objective="loyalty",
        region="Americas",
        countries=["USA"],
        total_budget=250000.0,
        start_date=date(2025, 3, 1),
        end_date=date(2025, 8, 31),
    )
    db_session.add(mandate)
    await db_session.commit()

    result = await db_session.execute(
        select(Mandate).where(Mandate.id == mandate.id)
    )
    fetched = result.scalar_one()
    d = fetched.to_dict()

    assert d["tenant_id"] == tenant_id
    assert d["name"] == "Dict Mandate"
    assert d["status"] == "draft"
    assert d["start_date"] == "2025-03-01"
    assert d["end_date"] == "2025-08-31"
    assert "created_at" in d
    assert "updated_at" in d


@pytest.mark.asyncio
async def test_mandate_tenant_isolation(db_session: AsyncSession):
    tenant_a = str(uuid4())
    tenant_b = str(uuid4())
    db_session.add(Mandate(
        tenant_id=tenant_a, client_id=str(uuid4()), name="A Mandate",
        objective="awareness", region="APAC", countries=["Japan"],
        total_budget=100000.0, start_date=date(2025, 1, 1), end_date=date(2025, 12, 31),
    ))
    db_session.add(Mandate(
        tenant_id=tenant_b, client_id=str(uuid4()), name="B Mandate",
        objective="conversion", region="EMEA", countries=["France"],
        total_budget=200000.0, start_date=date(2025, 1, 1), end_date=date(2025, 12, 31),
    ))
    await db_session.commit()

    result = await db_session.execute(
        select(Mandate).where(Mandate.tenant_id == tenant_a)
    )
    mandates = result.scalars().all()
    assert len(mandates) == 1
    assert mandates[0].name == "A Mandate"
