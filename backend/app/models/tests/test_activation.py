import pytest
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.activation import Activation


@pytest.mark.asyncio
async def test_create_activation(db_session: AsyncSession):
    tenant_id = str(uuid4())
    activation = Activation(
        tenant_id=tenant_id,
        campaign_id=str(uuid4()),
        channel="meta_ads",
        sub_channel="instagram_feed",
        audience_segment="brand_aware",
        budget_allocated=50000.0,
        currency="USD",
        platform_config={"age_min": 25, "age_max": 45, "interests": ["tech"]},
    )
    db_session.add(activation)
    await db_session.commit()

    result = await db_session.execute(
        select(Activation).where(Activation.tenant_id == tenant_id)
    )
    fetched = result.scalar_one()

    assert fetched.channel == "meta_ads"
    assert fetched.sub_channel == "instagram_feed"
    assert fetched.audience_segment == "brand_aware"
    assert fetched.budget_allocated == 50000.0
    assert fetched.status == "planned"
    assert fetched.platform_config["age_min"] == 25
    assert fetched.created_at is not None
    assert fetched.updated_at is not None


@pytest.mark.asyncio
async def test_activation_optional_sub_channel(db_session: AsyncSession):
    tenant_id = str(uuid4())
    activation = Activation(
        tenant_id=tenant_id,
        campaign_id=str(uuid4()),
        channel="google_ads",
        audience_segment="consideration",
        budget_allocated=30000.0,
        platform_config={},
    )
    db_session.add(activation)
    await db_session.commit()

    result = await db_session.execute(
        select(Activation).where(Activation.tenant_id == tenant_id)
    )
    fetched = result.scalar_one()
    assert fetched.sub_channel is None
    assert fetched.status == "planned"
    assert fetched.currency == "USD"


@pytest.mark.asyncio
async def test_activation_to_dict(db_session: AsyncSession):
    tenant_id = str(uuid4())
    activation = Activation(
        tenant_id=tenant_id,
        campaign_id=str(uuid4()),
        channel="linkedin_ads",
        audience_segment="decision_maker",
        budget_allocated=75000.0,
        status="active",
        platform_config={"job_titles": ["CTO", "VP Engineering"]},
    )
    db_session.add(activation)
    await db_session.commit()

    result = await db_session.execute(
        select(Activation).where(Activation.id == activation.id)
    )
    fetched = result.scalar_one()
    d = fetched.to_dict()

    assert d["tenant_id"] == tenant_id
    assert d["channel"] == "linkedin_ads"
    assert d["status"] == "active"
    assert d["platform_config"]["job_titles"] == ["CTO", "VP Engineering"]
    assert "created_at" in d
    assert "updated_at" in d


@pytest.mark.asyncio
async def test_activation_failed_status(db_session: AsyncSession):
    tenant_id = str(uuid4())
    activation = Activation(
        tenant_id=tenant_id,
        campaign_id=str(uuid4()),
        channel="meta_ads",
        audience_segment="retargeting",
        budget_allocated=10000.0,
        status="failed",
        platform_config={},
    )
    db_session.add(activation)
    await db_session.commit()

    result = await db_session.execute(
        select(Activation).where(Activation.tenant_id == tenant_id)
    )
    fetched = result.scalar_one()
    assert fetched.status == "failed"


@pytest.mark.asyncio
async def test_activation_tenant_isolation(db_session: AsyncSession):
    tenant_a = str(uuid4())
    tenant_b = str(uuid4())
    db_session.add(Activation(
        tenant_id=tenant_a, campaign_id=str(uuid4()),
        channel="meta_ads", audience_segment="brand_aware",
        budget_allocated=10000.0, platform_config={},
    ))
    db_session.add(Activation(
        tenant_id=tenant_b, campaign_id=str(uuid4()),
        channel="google_ads", audience_segment="consideration",
        budget_allocated=20000.0, platform_config={},
    ))
    await db_session.commit()

    result = await db_session.execute(
        select(Activation).where(Activation.tenant_id == tenant_a)
    )
    activations = result.scalars().all()
    assert len(activations) == 1
    assert activations[0].channel == "meta_ads"
