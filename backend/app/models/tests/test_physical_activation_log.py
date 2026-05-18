import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.physical_activation_log import PhysicalActivationLog


@pytest.mark.asyncio
async def test_create_physical_activation_log(db_session: AsyncSession):
    tenant_id = str(uuid4())
    event_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    log = PhysicalActivationLog(
        tenant_id=tenant_id,
        campaign_id=str(uuid4()),
        activation_id=str(uuid4()),
        event_type="impression",
        channel="meta_ads",
        payload={"placement": "feed", "device": "mobile", "impressions": 1200},
        logged_at=event_time,
    )
    db_session.add(log)
    await db_session.commit()

    result = await db_session.execute(
        select(PhysicalActivationLog).where(PhysicalActivationLog.tenant_id == tenant_id)
    )
    fetched = result.scalar_one()

    assert fetched.event_type == "impression"
    assert fetched.channel == "meta_ads"
    assert fetched.payload["impressions"] == 1200
    assert fetched.activation_id is not None
    assert fetched.created_at is not None


@pytest.mark.asyncio
async def test_physical_activation_log_no_activation_id(db_session: AsyncSession):
    tenant_id = str(uuid4())
    log = PhysicalActivationLog(
        tenant_id=tenant_id,
        campaign_id=str(uuid4()),
        event_type="campaign_start",
        channel="google_ads",
        payload={"start_time": "2025-07-01T00:00:00Z"},
        logged_at=datetime.now(timezone.utc),
    )
    db_session.add(log)
    await db_session.commit()

    result = await db_session.execute(
        select(PhysicalActivationLog).where(PhysicalActivationLog.tenant_id == tenant_id)
    )
    fetched = result.scalar_one()
    assert fetched.activation_id is None


@pytest.mark.asyncio
async def test_physical_activation_log_to_dict(db_session: AsyncSession):
    tenant_id = str(uuid4())
    log = PhysicalActivationLog(
        tenant_id=tenant_id,
        campaign_id=str(uuid4()),
        event_type="click",
        channel="linkedin_ads",
        payload={"url": "/landing", "clicks": 42},
        logged_at=datetime.now(timezone.utc),
    )
    db_session.add(log)
    await db_session.commit()

    result = await db_session.execute(
        select(PhysicalActivationLog).where(PhysicalActivationLog.id == log.id)
    )
    fetched = result.scalar_one()
    d = fetched.to_dict()

    assert d["tenant_id"] == tenant_id
    assert d["event_type"] == "click"
    assert d["channel"] == "linkedin_ads"
    assert d["payload"]["clicks"] == 42
    assert "logged_at" in d
    assert "created_at" in d
    assert "updated_at" not in d


@pytest.mark.asyncio
async def test_physical_activation_log_tenant_isolation(db_session: AsyncSession):
    tenant_a = str(uuid4())
    tenant_b = str(uuid4())
    now = datetime.now(timezone.utc)
    db_session.add(PhysicalActivationLog(
        tenant_id=tenant_a, campaign_id=str(uuid4()),
        event_type="impression", channel="meta_ads",
        payload={}, logged_at=now,
    ))
    db_session.add(PhysicalActivationLog(
        tenant_id=tenant_b, campaign_id=str(uuid4()),
        event_type="click", channel="google_ads",
        payload={}, logged_at=now,
    ))
    await db_session.commit()

    result = await db_session.execute(
        select(PhysicalActivationLog).where(PhysicalActivationLog.tenant_id == tenant_a)
    )
    logs = result.scalars().all()
    assert len(logs) == 1
    assert logs[0].event_type == "impression"
