"""Unit tests for PerformanceMetricService."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.services.performance_metric_service import PerformanceMetricService


def make_db(scalars_result=None, scalar_one=None):
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = scalars_result or []
    result.scalar_one_or_none.return_value = scalar_one
    db.execute = AsyncMock(return_value=result)
    return db


def make_metric(activation_id="act-001", metric_date=None):
    m = MagicMock()
    m.activation_id = activation_id
    m.date = metric_date or date(2026, 6, 1)
    m.metrics_json = {"impressions": 5000, "clicks": 200}
    m.source = "google_ads"
    m.tenant_id = "t-001"
    return m


# ── store_metric ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_store_metric_adds_and_commits():
    db = make_db()
    svc = PerformanceMetricService(db)

    result = await svc.store_metric(
        activation_id="act-001",
        date=date(2026, 6, 1),
        metrics_json={"impressions": 1000, "clicks": 50},
        source="google_ads",
        tenant_id="t-001",
    )

    db.add.assert_called_once()
    db.commit.assert_awaited_once()
    assert result is not None


@pytest.mark.asyncio
async def test_store_metric_creates_correct_object():
    db = make_db()
    svc = PerformanceMetricService(db)
    metrics = {"impressions": 2000, "ctr": 0.05, "spend": 300.0}

    await svc.store_metric("act-002", date(2026, 6, 2), metrics, "meta_ads", "t-002")

    added = db.add.call_args[0][0]
    assert added.activation_id == "act-002"
    assert added.metrics_json == metrics
    assert added.source == "meta_ads"
    assert added.tenant_id == "t-002"


# ── get_latest_metric ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_latest_metric_found():
    metric = make_metric()
    db = make_db(scalar_one=metric)
    svc = PerformanceMetricService(db)

    result = await svc.get_latest_metric("act-001", "t-001")

    assert result == metric
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_latest_metric_not_found():
    db = make_db(scalar_one=None)
    svc = PerformanceMetricService(db)

    result = await svc.get_latest_metric("act-999", "t-001")

    assert result is None


# ── get_metrics_for_date ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_metrics_for_date_returns_list():
    metrics = [make_metric("act-001"), make_metric("act-002")]
    db = make_db(scalars_result=metrics)
    svc = PerformanceMetricService(db)

    result = await svc.get_metrics_for_date(date(2026, 6, 1), "t-001")

    assert len(result) == 2
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_metrics_for_date_empty():
    db = make_db(scalars_result=[])
    svc = PerformanceMetricService(db)

    result = await svc.get_metrics_for_date(date(2026, 1, 1), "t-001")

    assert result == []


@pytest.mark.asyncio
async def test_get_metrics_for_date_tenant_isolation():
    db = make_db(scalars_result=[])
    svc = PerformanceMetricService(db)

    await svc.get_metrics_for_date(date(2026, 6, 1), "t-A")
    await svc.get_metrics_for_date(date(2026, 6, 1), "t-B")

    assert db.execute.await_count == 2
