"""Tests for AGT-15 Report Generator — TDD RED phase."""

import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.agents.report_generator import (
    DailyDigestBuilder,
    LLMNarrator,
    ReportAgent,
    TrendAnalyzer,
    WeeklyReportBuilder,
)
from backend.app.models.performance_metric import PerformanceMetric
from backend.app.models.report import Report
from backend.app.services.report_service import ReportService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _daily_dict(mandate_id="mandate-001", date_str="2026-05-12"):
    return {
        "report_type": "daily",
        "mandate_id": mandate_id,
        "date": date_str,
        "generated_at": f"{date_str}T08:05:00Z",
        "summary_by_channel": {"google_ads": {"total": 5, "red": 1, "amber": 2, "green": 2}},
        "activations": [],
        "red_alert_count": 1,
    }


def _weekly_dict(mandate_id="mandate-001"):
    return {
        "report_type": "weekly",
        "mandate_id": mandate_id,
        "week_start": "2026-05-06",
        "week_end": "2026-05-12",
        "generated_at": "2026-05-12T10:00:00Z",
        "summary_by_channel": {},
        "activations": [],
        "trends": {},
        "replan_recommendations": [],
        "executive_summary": "Campaign performed well.",
        "key_insights": ["Insight 1", "Insight 2", "Insight 3"],
        "red_alert_count": 0,
    }


def _analytics_summary(activations=None, date_str="2026-05-12"):
    return {
        "mandate_id": "mandate-001",
        "date": date_str,
        "summary_generated_at": f"{date_str}T08:00:00Z",
        "activations": activations or [],
        "red_alerts": [],
        "summary_by_channel": {},
    }


def _activation(act_id="act-1", channel="google_ads", status="green"):
    return {
        "activation_id": act_id,
        "campaign_id": "campaign-001",
        "channel": channel,
        "status": status,
        "kpi_results": [
            {"kpi_name": "ctr", "target": 3.0, "actual": 3.5,
             "achievement_percent": 16.7, "status": "green"}
        ],
        "metrics": {"impressions": 5000, "clicks": 250, "spend": 500.0, "conversions": 10},
    }


def _mock_anthropic(json_payload: dict):
    client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text=json.dumps(json_payload))]
    client.messages.create = AsyncMock(return_value=mock_resp)
    return client


# ---------------------------------------------------------------------------
# ReportService
# ---------------------------------------------------------------------------

class TestReportService:
    @pytest.mark.asyncio
    async def test_report_service_save_and_fetch(self):
        """save() calls db.add, db.commit, db.refresh with a Report instance."""
        db = AsyncMock()
        db.refresh = AsyncMock()

        service = ReportService(db)
        result = await service.save(_daily_dict(), "tenant-001")  # noqa: F841

        db.add.assert_called_once()
        added = db.add.call_args[0][0]
        assert isinstance(added, Report)
        assert added.mandate_id == "mandate-001"
        assert added.tenant_id == "tenant-001"
        assert added.report_type == "daily"
        assert added.period_start == date(2026, 5, 12)
        assert added.period_end == date(2026, 5, 12)
        db.commit.assert_called_once()
        db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_report_service_get_latest_returns_none(self):
        """get_latest() returns None when no matching report exists."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        service = ReportService(db)
        result = await service.get_latest("mandate-001", "daily", "tenant-001")

        assert result is None
        db.execute.assert_called_once()


# ---------------------------------------------------------------------------
# Helpers (continued)
# ---------------------------------------------------------------------------

def _perf_metric(activation_id, source, date_val, metrics):
    m = MagicMock(spec=PerformanceMetric)
    m.activation_id = activation_id
    m.source = source
    m.date = date_val
    m.metrics_json = metrics
    return m


# ---------------------------------------------------------------------------
# DailyDigestBuilder
# ---------------------------------------------------------------------------

class TestDailyDigestBuilder:
    def test_daily_digest_builder_structure(self):
        """build() returns correct keys and computes red_alert_count from red_alerts list."""
        summary = _analytics_summary(
            activations=[_activation("act-1", status="red")],
        )
        summary["red_alerts"] = [{"activation_id": "act-1"}]
        builder = DailyDigestBuilder()
        report = builder.build("mandate-001", summary)

        assert report["report_type"] == "daily"
        assert report["mandate_id"] == "mandate-001"
        assert report["date"] == "2026-05-12"
        assert "generated_at" in report
        assert "summary_by_channel" in report
        assert len(report["activations"]) == 1
        assert report["activations"][0]["activation_id"] == "act-1"
        assert report["red_alert_count"] == 1

    def test_daily_digest_builder_empty_activations(self):
        """build() with empty activations returns minimal valid dict."""
        summary = _analytics_summary()
        builder = DailyDigestBuilder()
        report = builder.build("mandate-001", summary)

        assert report["report_type"] == "daily"
        assert report["activations"] == []
        assert report["red_alert_count"] == 0


# ---------------------------------------------------------------------------
# TrendAnalyzer
# ---------------------------------------------------------------------------

class TestTrendAnalyzer:
    @pytest.mark.asyncio
    async def test_trend_analyzer_7day_aggregation(self):
        """analyze() sums impressions/clicks/spend/conversions per channel over 7 days."""
        rows = [
            _perf_metric("act-1", "google_ads", date(2026, 5, 6),
                         {"impressions": 1000, "clicks": 50, "spend": 100.0, "conversions": 5}),
            _perf_metric("act-1", "google_ads", date(2026, 5, 7),
                         {"impressions": 1200, "clicks": 60, "spend": 120.0, "conversions": 6}),
            _perf_metric("act-1", "google_ads", date(2026, 5, 8),
                         {"impressions": 1100, "clicks": 55, "spend": 110.0, "conversions": 5}),
            _perf_metric("act-1", "google_ads", date(2026, 5, 9),
                         {"impressions": 900, "clicks": 45, "spend": 90.0, "conversions": 4}),
            _perf_metric("act-1", "google_ads", date(2026, 5, 10),
                         {"impressions": 950, "clicks": 48, "spend": 95.0, "conversions": 4}),
            _perf_metric("act-1", "google_ads", date(2026, 5, 11),
                         {"impressions": 1050, "clicks": 52, "spend": 105.0, "conversions": 5}),
            _perf_metric("act-1", "google_ads", date(2026, 5, 12),
                         {"impressions": 1100, "clicks": 55, "spend": 110.0, "conversions": 6}),
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = rows
        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)

        analyzer = TrendAnalyzer(db)
        trends = await analyzer.analyze(["act-1"], "tenant-001", date(2026, 5, 12))

        assert "google_ads" in trends
        t = trends["google_ads"]
        assert t["impressions_7d"] == 7300
        assert t["clicks_7d"] == 365
        assert abs(t["spend_7d"] - 730.0) < 0.01
        assert t["conversions_7d"] == 35
        assert "trend" in t

    @pytest.mark.asyncio
    async def test_trend_analyzer_empty_metrics(self):
        """analyze() with empty activation_ids returns {} without querying DB."""
        db = AsyncMock()
        analyzer = TrendAnalyzer(db)
        result = await analyzer.analyze([], "tenant-001", date(2026, 5, 12))

        assert result == {}
        db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_trend_analyzer_improving_label(self):
        """Last-2-day avg spend >10% above prev-5-day avg → trend='improving'."""
        rows = []
        dates_prev = [date(2026, 5, 6), date(2026, 5, 7), date(2026, 5, 8),
                      date(2026, 5, 9), date(2026, 5, 10)]
        dates_last = [date(2026, 5, 11), date(2026, 5, 12)]
        for d in dates_prev:
            rows.append(_perf_metric("act-1", "google_ads", d,
                                     {"impressions": 0, "clicks": 0, "spend": 100.0, "conversions": 0}))
        for d in dates_last:
            rows.append(_perf_metric("act-1", "google_ads", d,
                                     {"impressions": 0, "clicks": 0, "spend": 150.0, "conversions": 0}))

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = rows
        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)

        analyzer = TrendAnalyzer(db)
        trends = await analyzer.analyze(["act-1"], "tenant-001", date(2026, 5, 12))

        assert trends["google_ads"]["trend"] == "improving"

    @pytest.mark.asyncio
    async def test_trend_analyzer_declining_label(self):
        """Last-2-day avg spend >10% below prev-5-day avg → trend='declining'."""
        rows = []
        dates_prev = [date(2026, 5, 6), date(2026, 5, 7), date(2026, 5, 8),
                      date(2026, 5, 9), date(2026, 5, 10)]
        dates_last = [date(2026, 5, 11), date(2026, 5, 12)]
        for d in dates_prev:
            rows.append(_perf_metric("act-1", "google_ads", d,
                                     {"impressions": 0, "clicks": 0, "spend": 150.0, "conversions": 0}))
        for d in dates_last:
            rows.append(_perf_metric("act-1", "google_ads", d,
                                     {"impressions": 0, "clicks": 0, "spend": 80.0, "conversions": 0}))

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = rows
        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)

        analyzer = TrendAnalyzer(db)
        trends = await analyzer.analyze(["act-1"], "tenant-001", date(2026, 5, 12))

        assert trends["google_ads"]["trend"] == "declining"


# ---------------------------------------------------------------------------
# WeeklyReportBuilder
# ---------------------------------------------------------------------------

class TestWeeklyReportBuilder:
    def test_weekly_report_builder_assembles_all_sections(self):
        """build() returns all required weekly report keys including trends and recommendations."""
        summary = _analytics_summary(activations=[_activation()])
        trends = {"google_ads": {"impressions_7d": 35000, "clicks_7d": 1750,
                                  "spend_7d": 3500.0, "conversions_7d": 49, "trend": "stable"}}
        recs = [{"activation_id": "act-1", "recommendation_type": "swap_creative",
                 "rationale": "Low CTR"}]
        builder = WeeklyReportBuilder()
        report = builder.build("mandate-001", summary, trends, recs)

        assert report["report_type"] == "weekly"
        assert report["mandate_id"] == "mandate-001"
        assert report["week_start"] == "2026-05-06"
        assert report["week_end"] == "2026-05-12"
        assert "generated_at" in report
        assert report["trends"] == trends
        assert report["replan_recommendations"] == recs
        assert "executive_summary" in report
        assert "key_insights" in report
        assert report["red_alert_count"] == 0

    def test_weekly_report_builder_no_recommendations(self):
        """build() with empty replan_recommendations sets replan_recommendations=[]."""
        summary = _analytics_summary()
        builder = WeeklyReportBuilder()
        report = builder.build("mandate-001", summary, {}, [])

        assert report["replan_recommendations"] == []
        assert report["activations"] == []


# ---------------------------------------------------------------------------
# LLMNarrator
# ---------------------------------------------------------------------------

class TestLLMNarrator:
    @pytest.mark.asyncio
    async def test_llm_narrator_happy_path(self):
        """narrate() parses LLM JSON and returns executive_summary + key_insights."""
        payload = {
            "executive_summary": "Campaign performed strongly.",
            "key_insights": ["CTR up 15%", "Spend on target", "Conversions exceeded goal"],
        }
        client = _mock_anthropic(payload)
        narrator = LLMNarrator(client)
        result = await narrator.narrate(_weekly_dict())

        assert result["executive_summary"] == "Campaign performed strongly."
        assert len(result["key_insights"]) == 3
        client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_llm_narrator_fallback_on_bad_json(self):
        """narrate() returns fallback strings when LLM returns unparseable JSON."""
        client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="not valid json {{")]
        client.messages.create = AsyncMock(return_value=mock_resp)

        narrator = LLMNarrator(client)
        result = await narrator.narrate(_weekly_dict())

        assert result["executive_summary"] == "Summary unavailable"
        assert result["key_insights"] == []


# ---------------------------------------------------------------------------
# ReportAgent — end-to-end
# ---------------------------------------------------------------------------

class TestReportAgent:
    @pytest.mark.asyncio
    async def test_report_agent_run_daily_end_to_end(self):
        """run_daily() returns a valid daily report dict with correct mandate_id."""
        db = AsyncMock()
        db.refresh = AsyncMock()
        client = MagicMock()

        agent = ReportAgent(db, client)
        summary = _analytics_summary(activations=[_activation("act-1", status="red")])
        summary["red_alerts"] = [{"activation_id": "act-1"}]

        report = await agent.run_daily("mandate-001", "tenant-001", summary)

        assert report["report_type"] == "daily"
        assert report["mandate_id"] == "mandate-001"
        assert report["red_alert_count"] == 1
        assert len(report["activations"]) == 1

    @pytest.mark.asyncio
    async def test_report_agent_run_weekly_end_to_end(self):
        """run_weekly() returns a valid weekly report with LLM narrative fields."""
        db = AsyncMock()
        db.refresh = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=mock_result)

        payload = {
            "executive_summary": "Strong week.",
            "key_insights": ["A", "B", "C"],
        }
        client = _mock_anthropic(payload)

        agent = ReportAgent(db, client)
        summary = _analytics_summary(activations=[_activation()])
        recs = [{"activation_id": "act-1", "recommendation_type": "swap_creative",
                 "rationale": "Low CTR", "estimated_cost_change": 5.0,
                 "channel": "google_ads", "direction": "underperforming",
                 "expected_impact": "...", "status": "pending_approval"}]

        report = await agent.run_weekly("mandate-001", "tenant-001", summary, recs)

        assert report["report_type"] == "weekly"
        assert report["mandate_id"] == "mandate-001"
        assert report["executive_summary"] == "Strong week."
        assert report["key_insights"] == ["A", "B", "C"]
        assert report["replan_recommendations"] == recs

    @pytest.mark.asyncio
    async def test_report_agent_run_weekly_persists_to_db(self):
        """run_weekly() calls db.add (via ReportService.save) to persist the report."""
        db = AsyncMock()
        db.refresh = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=mock_result)

        payload = {"executive_summary": "OK.", "key_insights": []}
        client = _mock_anthropic(payload)

        agent = ReportAgent(db, client)
        await agent.run_weekly("mandate-001", "tenant-001", _analytics_summary(), [])

        db.add.assert_called_once()
        db.commit.assert_called_once()
