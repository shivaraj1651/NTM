from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.performance_metric import PerformanceMetric


@pytest.mark.asyncio
async def test_create_performance_metric(db_session: AsyncSession):
    tenant_id = str(uuid4())
    pm = PerformanceMetric(
        tenant_id=tenant_id,
        activation_id=str(uuid4()),
        date=date(2026, 5, 1),
        metrics_json={"impressions": 10000, "clicks": 500, "spend": 250.0},
        source="google_ads",
    )
    db_session.add(pm)
    await db_session.commit()

    result = await db_session.execute(select(PerformanceMetric).where(PerformanceMetric.tenant_id == tenant_id))
    fetched = result.scalar_one()
    assert fetched.source == "google_ads"
    assert fetched.created_at is not None


@pytest.mark.asyncio
async def test_performance_metric_tenant_isolation(db_session: AsyncSession):
    t_a, t_b = str(uuid4()), str(uuid4())
    act = str(uuid4())
    db_session.add(PerformanceMetric(
        tenant_id=t_a, activation_id=act, date=date(2026, 1, 1),
        metrics_json={"clicks": 100}, source="meta_ads",
    ))
    db_session.add(PerformanceMetric(
        tenant_id=t_b, activation_id=act, date=date(2026, 1, 2),
        metrics_json={"clicks": 200}, source="meta_ads",
    ))
    await db_session.commit()

    result = await db_session.execute(select(PerformanceMetric).where(PerformanceMetric.tenant_id == t_a))
    assert len(result.scalars().all()) == 1


@pytest.mark.asyncio
async def test_performance_metric_to_dict(db_session: AsyncSession):
    tenant_id = str(uuid4())
    pm = PerformanceMetric(
        tenant_id=tenant_id, activation_id=str(uuid4()), date=date(2026, 3, 15),
        metrics_json={"roas": 3.5}, source="google_ads",
    )
    db_session.add(pm)
    await db_session.commit()
    result = await db_session.execute(select(PerformanceMetric).where(PerformanceMetric.id == pm.id))
    d = result.scalar_one().to_dict()
    assert d["tenant_id"] == tenant_id
    assert d["source"] == "google_ads"
