from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.budget import Budget


@pytest.mark.asyncio
async def test_create_budget(db_session: AsyncSession):
    tenant_id = str(uuid4())
    budget = Budget(
        tenant_id=tenant_id,
        campaign_id=str(uuid4()),
        total=1000000.0,
        currency="USD",
        breakdown={"meta_ads": 400000, "google_ads": 400000, "linkedin_ads": 200000},
    )
    db_session.add(budget)
    await db_session.commit()

    result = await db_session.execute(
        select(Budget).where(Budget.tenant_id == tenant_id)
    )
    fetched = result.scalar_one()

    assert fetched.total == 1000000.0
    assert fetched.currency == "USD"
    assert fetched.breakdown["meta_ads"] == 400000
    assert fetched.status == "draft"
    assert fetched.approved_by is None
    assert fetched.approved_at is None
    assert fetched.created_at is not None
    assert fetched.updated_at is not None


@pytest.mark.asyncio
async def test_budget_approval_fields(db_session: AsyncSession):
    approver_id = str(uuid4())
    approved_time = datetime.now(UTC)
    tenant_id = str(uuid4())
    budget = Budget(
        tenant_id=tenant_id,
        campaign_id=str(uuid4()),
        total=500000.0,
        currency="EUR",
        breakdown={},
        status="approved",
        approved_by=approver_id,
        approved_at=approved_time,
    )
    db_session.add(budget)
    await db_session.commit()

    result = await db_session.execute(
        select(Budget).where(Budget.tenant_id == tenant_id)
    )
    fetched = result.scalar_one()

    assert fetched.status == "approved"
    assert fetched.approved_by == approver_id
    assert fetched.approved_at is not None


@pytest.mark.asyncio
async def test_budget_to_dict(db_session: AsyncSession):
    tenant_id = str(uuid4())
    budget = Budget(
        tenant_id=tenant_id,
        campaign_id=str(uuid4()),
        total=250000.0,
        currency="GBP",
        breakdown={"channel_a": 125000, "channel_b": 125000},
    )
    db_session.add(budget)
    await db_session.commit()

    result = await db_session.execute(
        select(Budget).where(Budget.id == budget.id)
    )
    fetched = result.scalar_one()
    d = fetched.to_dict()

    assert d["tenant_id"] == tenant_id
    assert d["total"] == 250000.0
    assert d["currency"] == "GBP"
    assert d["status"] == "draft"
    assert d["approved_by"] is None
    assert d["approved_at"] is None
    assert "created_at" in d
    assert "updated_at" in d


@pytest.mark.asyncio
async def test_budget_tenant_isolation(db_session: AsyncSession):
    tenant_a = str(uuid4())
    tenant_b = str(uuid4())
    db_session.add(Budget(
        tenant_id=tenant_a, campaign_id=str(uuid4()),
        total=100000.0, breakdown={},
    ))
    db_session.add(Budget(
        tenant_id=tenant_b, campaign_id=str(uuid4()),
        total=200000.0, breakdown={},
    ))
    await db_session.commit()

    result = await db_session.execute(
        select(Budget).where(Budget.tenant_id == tenant_a)
    )
    budgets = result.scalars().all()
    assert len(budgets) == 1
    assert budgets[0].total == 100000.0
