"""ReportService — persist and retrieve Report records for AGT-15."""

import logging
from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.report import Report

logger = logging.getLogger(__name__)


class ReportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save(self, report_dict: dict, tenant_id: str) -> Report:
        """Persist a report dict to the report table and return the saved Report."""
        report_type = report_dict["report_type"]
        if report_type == "daily":
            period_start = date.fromisoformat(report_dict["date"])
            period_end = period_start
        else:
            period_start = date.fromisoformat(report_dict["week_start"])
            period_end = date.fromisoformat(report_dict["week_end"])

        report = Report(
            mandate_id=report_dict["mandate_id"],
            tenant_id=tenant_id,
            report_type=report_type,
            period_start=period_start,
            period_end=period_end,
            report_json=report_dict,
        )
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        return report

    async def get_latest(
        self,
        mandate_id: str,
        report_type: str,
        tenant_id: str,
    ) -> Optional[Report]:
        """Return the most recent Report for a mandate+type, or None."""
        stmt = (
            select(Report)
            .where(
                Report.mandate_id == mandate_id,
                Report.report_type == report_type,
                Report.tenant_id == tenant_id,
            )
            .order_by(Report.period_start.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
