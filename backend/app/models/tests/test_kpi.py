from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.kpi import KPI


@pytest.mark.asyncio
async def test_create_kpi(db_session: AsyncSession):
    tenant_id = str(uuid4())
    campaign_id = str(uuid4())
    kpi = KPI(
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        channel_enum="google_ads",
        audience_segment="brand_aware",
        kpi_name="conversion_rate",
        target_value=0.05,
        threshold_unit="percent",
    )
    db_session.add(kpi)
    await db_session.commit()

    result = await db_session.execute(select(KPI).where(KPI.tenant_id == tenant_id))
    fetched = result.scalar_one()
    assert fetched.kpi_name == "conversion_rate"
    assert fetched.target_value == 0.05
    assert fetched.created_at is not None


@pytest.mark.asyncio
async def test_kpi_tenant_isolation(db_session: AsyncSession):
    t_a, t_b = str(uuid4()), str(uuid4())
    camp = str(uuid4())
    db_session.add(KPI(tenant_id=t_a, campaign_id=camp, channel_enum="meta_ads",
                       audience_segment="seg1", kpi_name="ctr", target_value=0.02, threshold_unit="percent"))
    db_session.add(KPI(tenant_id=t_b, campaign_id=camp, channel_enum="meta_ads",
                       audience_segment="seg1", kpi_name="ctr", target_value=0.03, threshold_unit="percent"))
    await db_session.commit()

    result = await db_session.execute(select(KPI).where(KPI.tenant_id == t_a))
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].target_value == 0.02


@pytest.mark.asyncio
async def test_kpi_to_dict(db_session: AsyncSession):
    tenant_id = str(uuid4())
    kpi = KPI(
        tenant_id=tenant_id, campaign_id=str(uuid4()), channel_enum="linkedin_ads",
        audience_segment="consideration", kpi_name="impressions", target_value=50000.0,
        threshold_unit="count",
    )
    db_session.add(kpi)
    await db_session.commit()
    result = await db_session.execute(select(KPI).where(KPI.id == kpi.id))
    d = result.scalar_one().to_dict()
    assert d["tenant_id"] == tenant_id
    assert d["kpi_name"] == "impressions"
