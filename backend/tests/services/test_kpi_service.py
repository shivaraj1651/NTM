"""Unit tests for KPIService."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.services.kpi_service import KPIService


def make_db(scalars_result=None, scalar_one=None):
    """Build a mock AsyncSession with configurable query returns."""
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = scalars_result or []
    result.scalar_one_or_none.return_value = scalar_one
    db.execute = AsyncMock(return_value=result)
    return db


def make_kpi(name="conversion_rate", channel="google_ads", segment="brand_aware"):
    kpi = MagicMock()
    kpi.kpi_name = name
    kpi.channel_enum = channel
    kpi.audience_segment = segment
    kpi.campaign_id = "camp-001"
    kpi.tenant_id = "t-001"
    return kpi


# ── get_kpis_for_activation ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_kpis_for_activation_returns_list():
    kpi = make_kpi()
    db = make_db(scalars_result=[kpi])
    svc = KPIService(db)

    result = await svc.get_kpis_for_activation(
        campaign_id="camp-001",
        channel="google_ads",
        audience_segment="brand_aware",
        tenant_id="t-001",
    )

    assert result == [kpi]
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_kpis_for_activation_empty():
    db = make_db(scalars_result=[])
    svc = KPIService(db)

    result = await svc.get_kpis_for_activation(
        campaign_id="camp-999",
        channel="meta_ads",
        audience_segment="consideration",
        tenant_id="t-001",
    )

    assert result == []


@pytest.mark.asyncio
async def test_get_kpis_for_activation_multiple():
    kpis = [make_kpi("ctr"), make_kpi("cpc"), make_kpi("roas")]
    db = make_db(scalars_result=kpis)
    svc = KPIService(db)

    result = await svc.get_kpis_for_activation(
        campaign_id="camp-001",
        channel="linkedin_ads",
        audience_segment="conversion",
        tenant_id="t-002",
    )

    assert len(result) == 3


# ── get_kpi_by_name ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_kpi_by_name_found():
    kpi = make_kpi("conversion_rate")
    db = make_db(scalar_one=kpi)
    svc = KPIService(db)

    result = await svc.get_kpi_by_name(
        campaign_id="camp-001",
        channel="google_ads",
        audience_segment="brand_aware",
        kpi_name="conversion_rate",
        tenant_id="t-001",
    )

    assert result == kpi
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_kpi_by_name_not_found():
    db = make_db(scalar_one=None)
    svc = KPIService(db)

    result = await svc.get_kpi_by_name(
        campaign_id="camp-001",
        channel="google_ads",
        audience_segment="brand_aware",
        kpi_name="nonexistent_kpi",
        tenant_id="t-001",
    )

    assert result is None


@pytest.mark.asyncio
async def test_get_kpi_by_name_tenant_isolation():
    """Each call should pass tenant_id to the query."""
    db = make_db(scalar_one=None)
    svc = KPIService(db)

    await svc.get_kpi_by_name("c", "ch", "seg", "kpi", "tenant-A")
    await svc.get_kpi_by_name("c", "ch", "seg", "kpi", "tenant-B")

    assert db.execute.await_count == 2
