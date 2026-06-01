"""Unit tests for PerformanceMetric model."""

from datetime import date, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from backend.app.models.performance_metric import PerformanceMetric


@pytest.mark.asyncio
async def test_performance_metric_creation(db_session):
    """Test creating a PerformanceMetric record with flexible JSON metrics."""
    activation_id = str(uuid4())
    tenant_id = str(uuid4())

    metrics_json = {
        "impressions": 5000,
        "clicks": 250,
        "conversions": 7,
        "spend": 500.00,
        "ctr": 0.05,
        "cpc": 2.00,
        "cost_per_conversion": 71.43,
        "roas": 1.2
    }
    metric = PerformanceMetric(
        activation_id=activation_id,
        date=date.today(),
        metrics_json=metrics_json,
        source="google_ads",
        tenant_id=tenant_id
    )
    db_session.add(metric)
    await db_session.commit()

    result = await db_session.execute(
        select(PerformanceMetric).where(
            PerformanceMetric.activation_id == activation_id
        )
    )
    created = result.scalar_one()
    assert created.metrics_json["impressions"] == 5000
    assert created.source == "google_ads"
    assert str(created.activation_id) == activation_id
    assert str(created.tenant_id) == tenant_id


@pytest.mark.asyncio
async def test_performance_metric_one_per_day(db_session):
    """Test that we can have one metric row per activation per day."""
    activation_id = str(uuid4())
    tenant_id = str(uuid4())
    metric_date = date.today()

    metric1 = PerformanceMetric(
        activation_id=activation_id,
        date=metric_date,
        metrics_json={"impressions": 1000},
        source="google_ads",
        tenant_id=tenant_id
    )
    db_session.add(metric1)
    await db_session.commit()

    # Next day same activation should be allowed
    next_day = metric_date + timedelta(days=1)
    metric2 = PerformanceMetric(
        activation_id=activation_id,
        date=next_day,
        metrics_json={"impressions": 1200},
        source="google_ads",
        tenant_id=tenant_id
    )
    db_session.add(metric2)
    await db_session.commit()

    result = await db_session.execute(
        select(PerformanceMetric).where(
            PerformanceMetric.activation_id == activation_id
        )
    )
    metrics = result.scalars().all()
    assert len(metrics) == 2
    assert metrics[0].metrics_json["impressions"] == 1000
    assert metrics[1].metrics_json["impressions"] == 1200
