from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.campaign import Campaign


@pytest.mark.asyncio
async def test_create_campaign(db_session: AsyncSession):
    tenant_id = str(uuid4())
    campaign = Campaign(
        tenant_id=tenant_id,
        mandate_id=str(uuid4()),
        client_id=str(uuid4()),
        name="Q3 APAC Campaign",
        description="Full funnel push across APAC markets.",
    )
    db_session.add(campaign)
    await db_session.commit()

    result = await db_session.execute(
        select(Campaign).where(Campaign.tenant_id == tenant_id)
    )
    fetched = result.scalar_one()

    assert fetched.name == "Q3 APAC Campaign"
    assert fetched.description == "Full funnel push across APAC markets."
    assert fetched.status == "pending"
    assert fetched.created_at is not None
    assert fetched.updated_at is not None


@pytest.mark.asyncio
async def test_campaign_optional_fields(db_session: AsyncSession):
    tenant_id = str(uuid4())
    campaign = Campaign(
        tenant_id=tenant_id,
        name="Bare Campaign",
    )
    db_session.add(campaign)
    await db_session.commit()

    result = await db_session.execute(
        select(Campaign).where(Campaign.tenant_id == tenant_id)
    )
    fetched = result.scalar_one()

    assert fetched.status == "pending"
    assert fetched.mandate_id is None
    assert fetched.client_id is None
    assert fetched.description is None


@pytest.mark.asyncio
async def test_campaign_to_dict(db_session: AsyncSession):
    tenant_id = str(uuid4())
    campaign = Campaign(
        tenant_id=tenant_id,
        name="Dict Campaign",
        description="Testing to_dict.",
        status="planned",
    )
    db_session.add(campaign)
    await db_session.commit()

    result = await db_session.execute(
        select(Campaign).where(Campaign.id == campaign.id)
    )
    fetched = result.scalar_one()
    d = fetched.to_dict()

    assert d["tenant_id"] == tenant_id
    assert d["name"] == "Dict Campaign"
    assert d["description"] == "Testing to_dict."
    assert d["status"] == "planned"
    assert "created_at" in d
    assert "updated_at" in d


@pytest.mark.asyncio
async def test_campaign_tenant_isolation(db_session: AsyncSession):
    tenant_a = str(uuid4())
    tenant_b = str(uuid4())
    db_session.add(Campaign(tenant_id=tenant_a, name="Campaign A"))
    db_session.add(Campaign(tenant_id=tenant_b, name="Campaign B"))
    await db_session.commit()

    result = await db_session.execute(
        select(Campaign).where(Campaign.tenant_id == tenant_a)
    )
    campaigns = result.scalars().all()
    assert len(campaigns) == 1
    assert campaigns[0].name == "Campaign A"
