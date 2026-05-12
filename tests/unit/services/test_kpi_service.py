"""Tests for KPIService."""

import pytest
from uuid import uuid4
from backend.app.services.kpi_service import KPIService
from backend.app.models.kpi import KPI
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_get_kpis_for_activation(db_session: AsyncSession):
    """Test fetching KPIs for a specific activation."""
    campaign_id = str(uuid4())
    tenant_id = str(uuid4())

    # Create KPIs
    kpi1 = KPI(
        campaign_id=campaign_id,
        channel_enum="google_ads",
        audience_segment="brand_aware",
        kpi_name="conversion_rate",
        target_value=3.0,
        threshold_unit="percent",
        tenant_id=tenant_id
    )
    kpi2 = KPI(
        campaign_id=campaign_id,
        channel_enum="google_ads",
        audience_segment="brand_aware",
        kpi_name="cost_per_click",
        target_value=1.50,
        threshold_unit="currency",
        tenant_id=tenant_id
    )
    db_session.add(kpi1)
    db_session.add(kpi2)
    await db_session.commit()

    service = KPIService(db_session)
    kpis = await service.get_kpis_for_activation(
        campaign_id=campaign_id,
        channel="google_ads",
        audience_segment="brand_aware",
        tenant_id=tenant_id
    )

    assert len(kpis) == 2
    assert any(k.kpi_name == "conversion_rate" for k in kpis)
    assert any(k.kpi_name == "cost_per_click" for k in kpis)


@pytest.mark.asyncio
async def test_get_kpis_empty_result(db_session: AsyncSession):
    """Test fetching KPIs when none exist."""
    service = KPIService(db_session)
    kpis = await service.get_kpis_for_activation(
        campaign_id=str(uuid4()),
        channel="google_ads",
        audience_segment="unknown",
        tenant_id=str(uuid4())
    )

    assert len(kpis) == 0


@pytest.mark.asyncio
async def test_get_kpi_by_name(db_session: AsyncSession):
    """Test fetching a specific KPI by name."""
    campaign_id = str(uuid4())
    tenant_id = str(uuid4())

    # Create a KPI
    kpi = KPI(
        campaign_id=campaign_id,
        channel_enum="linkedin_ads",
        audience_segment="consideration",
        kpi_name="click_through_rate",
        target_value=2.5,
        threshold_unit="percent",
        tenant_id=tenant_id
    )
    db_session.add(kpi)
    await db_session.commit()

    service = KPIService(db_session)
    result = await service.get_kpi_by_name(
        campaign_id=campaign_id,
        channel="linkedin_ads",
        audience_segment="consideration",
        kpi_name="click_through_rate",
        tenant_id=tenant_id
    )

    assert result is not None
    assert result.kpi_name == "click_through_rate"
    assert result.target_value == 2.5


@pytest.mark.asyncio
async def test_get_kpi_by_name_not_found(db_session: AsyncSession):
    """Test fetching a KPI by name when it doesn't exist."""
    service = KPIService(db_session)
    result = await service.get_kpi_by_name(
        campaign_id=str(uuid4()),
        channel="google_ads",
        audience_segment="brand_aware",
        kpi_name="nonexistent_metric",
        tenant_id=str(uuid4())
    )

    assert result is None
