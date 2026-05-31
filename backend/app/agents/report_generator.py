"""ReportAgent (AGT-15) — daily and weekly campaign report generation.

Consumes AGT-13 AnalyticsSummary and AGT-14 ReplanRecommendations to produce
structured reports for internal (operational) and external (executive) audiences.

TASK-022
"""

import json
import logging
from backend.app.agents.json_parsing import extract_json
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.performance_metric import PerformanceMetric
from backend.app.services.report_service import ReportService
from backend.app.external.stubs import stub_enabled

logger = logging.getLogger(__name__)


class DailyDigestBuilder:
    def build(self, mandate_id: str, analytics_summary: dict) -> dict:
        activations = analytics_summary.get("activations", [])
        red_alerts = analytics_summary.get("red_alerts", [])
        return {
            "report_type": "daily",
            "mandate_id": mandate_id,
            "date": analytics_summary.get("date", datetime.utcnow().date().isoformat()),
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "summary_by_channel": analytics_summary.get("summary_by_channel", {}),
            "activations": [
                {
                    "activation_id": a["activation_id"],
                    "channel": a.get("channel", ""),
                    "status": a.get("status", ""),
                    "kpi_results": a.get("kpi_results", []),
                }
                for a in activations
            ],
            "red_alert_count": len(red_alerts),
        }


class TrendAnalyzer:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze(
        self,
        activation_ids: list,
        tenant_id: str,
        week_end: date,
    ) -> dict:
        if not activation_ids:
            return {}

        week_start = week_end - timedelta(days=6)
        stmt = (
            select(PerformanceMetric)
            .where(
                PerformanceMetric.activation_id.in_(activation_ids),
                PerformanceMetric.tenant_id == tenant_id,
                PerformanceMetric.date >= week_start,
                PerformanceMetric.date <= week_end,
            )
            .order_by(PerformanceMetric.date)
        )
        result = await self.db.execute(stmt)
        rows = result.scalars().all()

        if not rows:
            return {}

        channel_data: dict = {}
        for row in rows:
            ch = row.source
            if ch not in channel_data:
                channel_data[ch] = {
                    "impressions_7d": 0,
                    "clicks_7d": 0,
                    "spend_7d": 0.0,
                    "conversions_7d": 0,
                    "daily_spends": {},
                }
            m = row.metrics_json or {}
            channel_data[ch]["impressions_7d"] += m.get("impressions", 0)
            channel_data[ch]["clicks_7d"] += m.get("clicks", 0)
            channel_data[ch]["spend_7d"] += m.get("spend", 0.0)
            channel_data[ch]["conversions_7d"] += m.get("conversions", 0)
            d_str = row.date.isoformat()
            channel_data[ch]["daily_spends"][d_str] = (
                channel_data[ch]["daily_spends"].get(d_str, 0.0) + m.get("spend", 0.0)
            )

        return {
            ch: {
                "impressions_7d": data["impressions_7d"],
                "clicks_7d": data["clicks_7d"],
                "spend_7d": data["spend_7d"],
                "conversions_7d": data["conversions_7d"],
                "trend": self._compute_trend([v for _, v in sorted(data["daily_spends"].items())]),
            }
            for ch, data in channel_data.items()
        }

    @staticmethod
    def _compute_trend(daily_spends: list) -> str:
        if len(daily_spends) < 2:
            return "insufficient_data"
        last_2 = daily_spends[-2:]
        prev_n = daily_spends[:-2]
        if not prev_n:
            return "insufficient_data"
        last_2_avg = sum(last_2) / len(last_2)
        prev_avg = sum(prev_n) / len(prev_n)
        if prev_avg == 0:
            return "stable"
        delta_pct = ((last_2_avg - prev_avg) / prev_avg) * 100
        if delta_pct > 10:
            return "improving"
        if delta_pct < -10:
            return "declining"
        return "stable"


class WeeklyReportBuilder:
    def build(
        self,
        mandate_id: str,
        analytics_summary: dict,
        trends: dict,
        replan_recommendations: list,
    ) -> dict:
        date_str = analytics_summary.get("date", datetime.utcnow().date().isoformat())
        week_end = date.fromisoformat(date_str)
        week_start = week_end - timedelta(days=6)
        activations = analytics_summary.get("activations", [])
        red_alerts = analytics_summary.get("red_alerts", [])
        return {
            "report_type": "weekly",
            "mandate_id": mandate_id,
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "summary_by_channel": analytics_summary.get("summary_by_channel", {}),
            "activations": [
                {
                    "activation_id": a["activation_id"],
                    "channel": a.get("channel", ""),
                    "status": a.get("status", ""),
                    "kpi_results": a.get("kpi_results", []),
                }
                for a in activations
            ],
            "trends": trends,
            "replan_recommendations": replan_recommendations,
            "executive_summary": "",
            "key_insights": [],
            "red_alert_count": len(red_alerts),
        }


class LLMNarrator:
    _MODEL = "claude-haiku-4-5-20251001"
    _MAX_TOKENS = 512
    _SYSTEM = "You are a marketing performance analyst. Write concise, client-appropriate summaries."

    def __init__(self, anthropic_client: Any):
        self.client = anthropic_client

    async def narrate(self, weekly_report: dict) -> dict:
        user_message = (
            "Summarize the following weekly campaign performance report in 2-3 sentences "
            "(executive_summary) and provide exactly 3 key insights as a JSON list (key_insights). "
            'Return JSON only: {"executive_summary": "...", "key_insights": ["...", "...", "..."]}\n\n'
            + json.dumps(weekly_report)
        )
        # NTM_STUB_EXTERNAL: stubbed external call
        if stub_enabled():
            logger.info("Report generator LLM narrator stubbed (NTM_STUB_EXTERNAL)")
            return {
                "executive_summary": "Stub weekly summary (NTM_STUB_EXTERNAL).",
                "key_insights": ["Stub insight 1", "Stub insight 2", "Stub insight 3"],
            }
        try:
            response = await self.client.messages.create(
                model=self._MODEL,
                max_tokens=self._MAX_TOKENS,
                system=self._SYSTEM,
                messages=[{"role": "user", "content": user_message}],
            )
            raw = response.content[0].text
            parsed = extract_json(raw)
            return {
                "executive_summary": parsed.get("executive_summary", "Summary unavailable"),
                "key_insights": parsed.get("key_insights", []),
            }
        except Exception as exc:
            logger.warning("LLM narration failed (%s) — applying fallback", exc)
            return {"executive_summary": "Summary unavailable", "key_insights": []}


class ReportAgent:
    def __init__(self, db_session: AsyncSession, anthropic_client: Any):
        self.db = db_session
        self.daily_builder = DailyDigestBuilder()
        self.trend_analyzer = TrendAnalyzer(db_session)
        self.weekly_builder = WeeklyReportBuilder()
        self.narrator = LLMNarrator(anthropic_client)
        self.report_service = ReportService(db_session)

    async def run_daily(
        self,
        mandate_id: str,
        tenant_id: str,
        analytics_summary: dict,
    ) -> dict:
        report = self.daily_builder.build(mandate_id, analytics_summary)
        try:
            await self.report_service.save(report, tenant_id)
        except Exception as exc:
            logger.error("Failed to persist daily report for %s: %s", mandate_id, exc)
        return report

    async def run_weekly(
        self,
        mandate_id: str,
        tenant_id: str,
        analytics_summary: dict,
        replan_recommendations: list,
    ) -> dict:
        activation_ids = [
            a["activation_id"] for a in analytics_summary.get("activations", [])
        ]
        date_str = analytics_summary.get("date", datetime.utcnow().date().isoformat())
        week_end = date.fromisoformat(date_str)

        try:
            trends = await self.trend_analyzer.analyze(activation_ids, tenant_id, week_end)
        except Exception as exc:
            logger.warning("TrendAnalyzer failed for %s: %s — proceeding with empty trends", mandate_id, exc)
            trends = {}

        report = self.weekly_builder.build(
            mandate_id, analytics_summary, trends, replan_recommendations
        )

        narrative = await self.narrator.narrate(report)
        report["executive_summary"] = narrative["executive_summary"]
        report["key_insights"] = narrative["key_insights"]

        try:
            await self.report_service.save(report, tenant_id)
        except Exception as exc:
            logger.error("Failed to persist weekly report for %s: %s", mandate_id, exc)

        return report
