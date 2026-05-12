"""Tests for PerformanceMetricService."""

import pytest
from datetime import date, timedelta
from uuid import uuid4
from backend.app.services.performance_metric_service import PerformanceMetricService
from backend.app.models.performance_metric import PerformanceMetric
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_store_metric(db_session: AsyncSession):
    """Test storing a performance metric."""
    activation_id = str(uuid4())
    tenant_id = str(uuid4())
    metrics = {"impressions": 5000, "clicks": 250, "conversions": 7, "spend": 500.00}

    service = PerformanceMetricService(db_session)
    metric = await service.store_metric(
        activation_id=activation_id,
        date=date.today(),
        metrics_json=metrics,
        source="google_ads",
        tenant_id=tenant_id
    )

    assert metric.activation_id == activation_id
    assert metric.metrics_json["impressions"] == 5000
    assert metric.source == "google_ads"


@pytest.mark.asyncio
async def test_get_latest_metric(db_session: AsyncSession):
    """Test retrieving the most recent metric for an activation."""
    activation_id = str(uuid4())
    tenant_id = str(uuid4())

    service = PerformanceMetricService(db_session)

    # Store two metrics on different days
    today = date.today()
    yesterday = today - timedelta(days=1)

    metric1 = await service.store_metric(
        activation_id=activation_id,
        date=yesterday,
        metrics_json={"impressions": 4000},
        source="google_ads",
        tenant_id=tenant_id
    )

    metric2 = await service.store_metric(
        activation_id=activation_id,
        date=today,
        metrics_json={"impressions": 5000},
        source="google_ads",
        tenant_id=tenant_id
    )

    latest = await service.get_latest_metric(activation_id, tenant_id)
    assert latest.date == today
    assert latest.metrics_json["impressions"] == 5000


@pytest.mark.asyncio
async def test_get_metrics_for_date(db_session: AsyncSession):
    """Test retrieving all metrics for a specific date."""
    tenant_id = str(uuid4())
    target_date = date.today()

    service = PerformanceMetricService(db_session)

    # Store metrics for same date, different activations
    activation_id_1 = str(uuid4())
    activation_id_2 = str(uuid4())

    metric1 = await service.store_metric(
        activation_id=activation_id_1,
        date=target_date,
        metrics_json={"impressions": 1000},
        source="google_ads",
        tenant_id=tenant_id
    )

    metric2 = await service.store_metric(
        activation_id=activation_id_2,
        date=target_date,
        metrics_json={"impressions": 2000},
        source="meta_ads",
        tenant_id=tenant_id
    )

    # Store metric for different date (should not be included)
    await service.store_metric(
        activation_id=activation_id_1,
        date=target_date - timedelta(days=1),
        metrics_json={"impressions": 500},
        source="google_ads",
        tenant_id=tenant_id
    )

    metrics = await service.get_metrics_for_date(target_date, tenant_id)
    assert len(metrics) == 2
    assert metric1 in metrics
    assert metric2 in metrics
