"""ReportAgent (AGT-15) — daily and weekly campaign report generation.

Consumes AGT-13 AnalyticsSummary and AGT-14 ReplanRecommendations to produce
structured reports for internal (operational) and external (executive) audiences.

TASK-022
"""

import json
import logging
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.performance_metric import PerformanceMetric
from backend.app.services.report_service import ReportService

logger = logging.getLogger(__name__)


class DailyDigestBuilder:
    def build(self, mandate_id: str, analytics_summary: dict) -> dict:
        raise NotImplementedError


class TrendAnalyzer:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze(self, activation_ids: list, tenant_id: str, week_end: date) -> dict:
        raise NotImplementedError


class WeeklyReportBuilder:
    def build(self, mandate_id: str, analytics_summary: dict, trends: dict, replan_recommendations: list) -> dict:
        raise NotImplementedError


class LLMNarrator:
    def __init__(self, anthropic_client: Any):
        self.client = anthropic_client

    async def narrate(self, weekly_report: dict) -> dict:
        raise NotImplementedError


class ReportAgent:
    def __init__(self, db_session: AsyncSession, anthropic_client: Any):
        self.db = db_session
        self.daily_builder = DailyDigestBuilder()
        self.trend_analyzer = TrendAnalyzer(db_session)
        self.weekly_builder = WeeklyReportBuilder()
        self.narrator = LLMNarrator(anthropic_client)
        self.report_service = ReportService(db_session)

    async def run_daily(self, mandate_id: str, tenant_id: str, analytics_summary: dict) -> dict:
        raise NotImplementedError

    async def run_weekly(self, mandate_id: str, tenant_id: str, analytics_summary: dict, replan_recommendations: list) -> dict:
        raise NotImplementedError
