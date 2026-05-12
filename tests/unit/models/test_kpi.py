"""Unit tests for KPI model."""

import pytest
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from backend.app.models.kpi import KPI


@pytest.mark.asyncio
async def test_kpi_creation(db_session):
    """Test creating a KPI record with all required fields."""
    campaign_id = str(uuid4())
    tenant_id = str(uuid4())

    kpi = KPI(
        campaign_id=campaign_id,
        channel_enum="google_ads",
        audience_segment="brand_aware",
        kpi_name="conversion_rate",
        target_value=3.0,
        threshold_unit="percent",
        tenant_id=tenant_id
    )
    db_session.add(kpi)
    await db_session.commit()

    result = await db_session.execute(
        select(KPI).where(KPI.campaign_id == campaign_id)
    )
    created_kpi = result.scalar_one()
    assert created_kpi.kpi_name == "conversion_rate"
    assert created_kpi.target_value == 3.0
    assert created_kpi.threshold_unit == "percent"
    assert created_kpi.tenant_id == tenant_id


@pytest.mark.asyncio
async def test_kpi_unique_constraint(db_session):
    """Test unique constraint: (campaign_id, channel_enum, audience_segment, kpi_name, tenant_id)."""
    campaign_id = str(uuid4())
    tenant_id = str(uuid4())

    kpi1 = KPI(
        campaign_id=campaign_id,
        channel_enum="google_ads",
        audience_segment="brand_aware",
        kpi_name="conversion_rate",
        target_value=3.0,
        threshold_unit="percent",
        tenant_id=tenant_id
    )
    db_session.add(kpi1)
    await db_session.commit()

    kpi2 = KPI(
        campaign_id=campaign_id,
        channel_enum="google_ads",
        audience_segment="brand_aware",
        kpi_name="conversion_rate",
        target_value=4.0,
        threshold_unit="percent",
        tenant_id=tenant_id
    )
    db_session.add(kpi2)

    with pytest.raises(IntegrityError):
        await db_session.commit()
