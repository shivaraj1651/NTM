import pytest
from uuid import uuid4
from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.report import Report


@pytest.mark.asyncio
async def test_create_report(db_session: AsyncSession):
    tenant_id = str(uuid4())
    report = Report(
        tenant_id=tenant_id,
        mandate_id=str(uuid4()),
        report_type="daily",
        period_start=date(2026, 5, 1),
        period_end=date(2026, 5, 1),
        report_json={"summary": "Campaign exceeded targets by 12%.", "score": 88},
    )
    db_session.add(report)
    await db_session.commit()

    result = await db_session.execute(select(Report).where(Report.tenant_id == tenant_id))
    fetched = result.scalar_one()
    assert fetched.report_type == "daily"
    assert fetched.created_at is not None


@pytest.mark.asyncio
async def test_report_tenant_isolation(db_session: AsyncSession):
    t_a, t_b = str(uuid4()), str(uuid4())
    db_session.add(Report(tenant_id=t_a, mandate_id=str(uuid4()), report_type="weekly",
                          period_start=date(2026, 4, 1), period_end=date(2026, 4, 7),
                          report_json={"title": "R-A"}))
    db_session.add(Report(tenant_id=t_b, mandate_id=str(uuid4()), report_type="weekly",
                          period_start=date(2026, 4, 1), period_end=date(2026, 4, 7),
                          report_json={"title": "R-B"}))
    await db_session.commit()

    result = await db_session.execute(select(Report).where(Report.tenant_id == t_a))
    rows = result.scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_report_to_dict(db_session: AsyncSession):
    tenant_id = str(uuid4())
    report = Report(
        tenant_id=tenant_id, mandate_id=str(uuid4()), report_type="daily",
        period_start=date(2026, 5, 18), period_end=date(2026, 5, 18),
        report_json={"insights": []},
    )
    db_session.add(report)
    await db_session.commit()
    result = await db_session.execute(select(Report).where(Report.id == report.id))
    d = result.scalar_one().to_dict()
    assert d["tenant_id"] == tenant_id
    assert d["report_type"] == "daily"
