# AGT-15 Report Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement AGT-15 ReportAgent that consumes AGT-13/AGT-14 outputs to produce daily and weekly campaign performance reports, persists them to a `report` table, and enriches weekly reports with LLM-generated executive summaries.

**Architecture:** Four inner classes (DailyDigestBuilder, TrendAnalyzer, WeeklyReportBuilder, LLMNarrator) compose under a ReportAgent orchestrator in one file. Daily reports are pure data transforms. Weekly reports add a 7-day PerformanceMetric DB query and a single Haiku LLM call. All reports persist via ReportService.

**Tech Stack:** Python 3.12, SQLAlchemy async, Anthropic SDK (`claude-haiku-4-5-20251001`), Celery Beat, pytest-asyncio

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `backend/app/models/report.py` | Create | Report SQLAlchemy model |
| `backend/alembic/versions/2026_05_13_00_create_report_table.py` | Create | Alembic migration |
| `backend/app/services/report_service.py` | Create | ReportService: save + get_latest |
| `backend/app/agents/report_generator.py` | Create | DailyDigestBuilder, TrendAnalyzer, WeeklyReportBuilder, LLMNarrator, ReportAgent |
| `backend/app/tasks/report_tasks.py` | Create | Celery Beat: daily (09:00 UTC) + weekly (Mon 10:00 UTC) |
| `backend/tests/agents/test_report_generator.py` | Create | 15 tests (TDD RED → GREEN) |

---

### Task 1: Report DB Model + Alembic Migration

**Files:**
- Create: `backend/app/models/report.py`
- Create: `backend/alembic/versions/2026_05_13_00_create_report_table.py`

- [ ] **Step 1: Create the Report model**

```python
# backend/app/models/report.py
"""SQLAlchemy model for Report — persisted output of AGT-15 ReportAgent."""

from uuid import uuid4
from datetime import datetime, date
from sqlalchemy import Column, Date, DateTime, String, Index
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import UUID, JSON

Base = declarative_base()


class Report(Base):
    __tablename__ = "report"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    mandate_id = Column(String, nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    report_type = Column(String(10), nullable=False)   # "daily" | "weekly"
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    report_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_report_mandate_type_start", "mandate_id", "report_type", "period_start"),
        Index("ix_report_tenant_type", "tenant_id", "report_type"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "mandate_id": self.mandate_id,
            "tenant_id": self.tenant_id,
            "report_type": self.report_type,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "report_json": self.report_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
```

- [ ] **Step 2: Create the Alembic migration**

```python
# backend/alembic/versions/2026_05_13_00_create_report_table.py
"""Create report table for AGT-15.

Revision ID: 2026_05_13_00
Revises: 2026_05_12_01
Create Date: 2026-05-13 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '2026_05_13_00'
down_revision = '2026_05_12_01'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'report',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('mandate_id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('report_type', sa.String(10), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('report_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_report_mandate_id', 'report', ['mandate_id'])
    op.create_index('ix_report_tenant_id', 'report', ['tenant_id'])
    op.create_index(
        'ix_report_mandate_type_start', 'report',
        ['mandate_id', 'report_type', 'period_start'],
    )
    op.create_index(
        'ix_report_tenant_type', 'report',
        ['tenant_id', 'report_type'],
    )


def downgrade() -> None:
    op.drop_table('report')
```

- [ ] **Step 3: Verify model imports cleanly**

```bash
cd backend && python -c "from app.models.report import Report; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/report.py backend/alembic/versions/2026_05_13_00_create_report_table.py
git commit -m "[TASK-022] feat: add Report model and Alembic migration for AGT-15"
```

---

### Task 2: ReportService

**Files:**
- Create: `backend/app/services/report_service.py`
- Create (tests section): `backend/tests/agents/test_report_generator.py` (ReportService tests only — rest added in Task 3)

- [ ] **Step 1: Write the two failing ReportService tests**

Create `backend/tests/agents/test_report_generator.py` with just these two tests:

```python
"""Tests for AGT-15 Report Generator — TDD RED phase."""

import json
import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, call, patch

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
        result = await service.save(_daily_dict(), "tenant-001")

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
```

- [ ] **Step 2: Run to confirm FAIL**

```bash
cd backend && python -m pytest tests/agents/test_report_generator.py::TestReportService -v
```

Expected: `ImportError` (ReportService not yet created)

- [ ] **Step 3: Implement ReportService**

```python
# backend/app/services/report_service.py
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
```

- [ ] **Step 4: Run to confirm PASS**

```bash
cd backend && python -m pytest tests/agents/test_report_generator.py::TestReportService -v
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/report_service.py backend/tests/agents/test_report_generator.py
git commit -m "[TASK-022] feat: add ReportService with save and get_latest"
```

---

### Task 3: Write All Remaining Tests (RED Phase) + Scaffold report_generator.py

**Files:**
- Create: `backend/app/agents/report_generator.py` (stub only — makes imports resolve)
- Modify: `backend/tests/agents/test_report_generator.py` (add imports + 13 more tests)

- [ ] **Step 1: Scaffold `report_generator.py` (stubs only)**

Create `backend/app/agents/report_generator.py`:

```python
# backend/app/agents/report_generator.py
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
```

- [ ] **Step 2: Add imports + 13 remaining tests to `test_report_generator.py`**

Add these two imports at the top of `backend/tests/agents/test_report_generator.py`, after the existing imports (`from backend.app.services.report_service import ReportService`):

```python
from backend.app.agents.report_generator import (
    DailyDigestBuilder,
    TrendAnalyzer,
    WeeklyReportBuilder,
    LLMNarrator,
    ReportAgent,
)
from backend.app.models.performance_metric import PerformanceMetric
```

Then append the following below the existing `TestReportService` class:

```python


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
        # prev 5 days: 100 each → avg 100; last 2 days: 150 each → avg 150 (+50%)
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
        # prev 5 days: 150 each → avg 150; last 2 days: 80 each → avg 80 (-47%)
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
```

- [ ] **Step 3: Run all 15 tests to confirm RED (NotImplementedError or similar failures)**

```bash
cd backend && python -m pytest tests/agents/test_report_generator.py -v 2>&1 | tail -20
```

Expected: `2 passed, 13 failed` (ReportService tests still pass; rest fail with `NotImplementedError`)

- [ ] **Step 4: Commit the RED phase**

```bash
git add backend/app/agents/report_generator.py backend/tests/agents/test_report_generator.py
git commit -m "[TASK-022] test: add 15 AGT-15 tests (RED phase)"
```

---

### Task 4: Implement DailyDigestBuilder

**Files:**
- Modify: `backend/app/agents/report_generator.py` (replace DailyDigestBuilder stub)

- [ ] **Step 1: Replace the DailyDigestBuilder stub**

In `backend/app/agents/report_generator.py`, replace the `DailyDigestBuilder` class with:

```python
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
```

- [ ] **Step 2: Run DailyDigestBuilder tests**

```bash
cd backend && python -m pytest tests/agents/test_report_generator.py::TestDailyDigestBuilder -v
```

Expected: `2 passed`

- [ ] **Step 3: Commit**

```bash
git add backend/app/agents/report_generator.py
git commit -m "[TASK-022] feat: implement DailyDigestBuilder for AGT-15"
```

---

### Task 5: Implement TrendAnalyzer

**Files:**
- Modify: `backend/app/agents/report_generator.py` (replace TrendAnalyzer stub)

- [ ] **Step 1: Replace the TrendAnalyzer stub**

```python
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

        # Aggregate per channel
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
                "trend": self._compute_trend(sorted(data["daily_spends"].values())),
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
```

- [ ] **Step 2: Run TrendAnalyzer tests**

```bash
cd backend && python -m pytest tests/agents/test_report_generator.py::TestTrendAnalyzer -v
```

Expected: `4 passed`

- [ ] **Step 3: Commit**

```bash
git add backend/app/agents/report_generator.py
git commit -m "[TASK-022] feat: implement TrendAnalyzer with 7-day trend labels"
```

---

### Task 6: Implement WeeklyReportBuilder

**Files:**
- Modify: `backend/app/agents/report_generator.py` (replace WeeklyReportBuilder stub)

- [ ] **Step 1: Replace the WeeklyReportBuilder stub**

```python
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
```

- [ ] **Step 2: Run WeeklyReportBuilder tests**

```bash
cd backend && python -m pytest tests/agents/test_report_generator.py::TestWeeklyReportBuilder -v
```

Expected: `2 passed`

- [ ] **Step 3: Commit**

```bash
git add backend/app/agents/report_generator.py
git commit -m "[TASK-022] feat: implement WeeklyReportBuilder for AGT-15"
```

---

### Task 7: Implement LLMNarrator

**Files:**
- Modify: `backend/app/agents/report_generator.py` (replace LLMNarrator stub)

- [ ] **Step 1: Replace the LLMNarrator stub**

```python
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
        try:
            response = await self.client.messages.create(
                model=self._MODEL,
                max_tokens=self._MAX_TOKENS,
                system=self._SYSTEM,
                messages=[{"role": "user", "content": user_message}],
            )
            raw = response.content[0].text
            parsed = json.loads(raw)
            return {
                "executive_summary": parsed.get("executive_summary", "Summary unavailable"),
                "key_insights": parsed.get("key_insights", []),
            }
        except Exception as exc:
            logger.warning("LLM narration failed (%s) — applying fallback", exc)
            return {"executive_summary": "Summary unavailable", "key_insights": []}
```

- [ ] **Step 2: Run LLMNarrator tests**

```bash
cd backend && python -m pytest tests/agents/test_report_generator.py::TestLLMNarrator -v
```

Expected: `2 passed`

- [ ] **Step 3: Commit**

```bash
git add backend/app/agents/report_generator.py
git commit -m "[TASK-022] feat: implement LLMNarrator with Haiku + fallback for AGT-15"
```

---

### Task 8: Implement ReportAgent Orchestrator

**Files:**
- Modify: `backend/app/agents/report_generator.py` (replace ReportAgent stub)

- [ ] **Step 1: Replace the ReportAgent stub**

```python
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
```

- [ ] **Step 2: Run all 15 tests**

```bash
cd backend && python -m pytest tests/agents/test_report_generator.py -v
```

Expected: `15 passed`

- [ ] **Step 3: Commit**

```bash
git add backend/app/agents/report_generator.py
git commit -m "[TASK-022] feat: implement ReportAgent orchestrator — AGT-15 complete"
```

---

### Task 9: Celery Report Tasks

**Files:**
- Create: `backend/app/tasks/report_tasks.py`

- [ ] **Step 1: Create the Celery tasks file**

```python
# backend/app/tasks/report_tasks.py
"""Celery tasks for daily and weekly report generation (AGT-15).

Schedules:
  generate_daily_report_task  — Daily 09:00 UTC (after AGT-13 at 08:00)
  generate_weekly_report_task — Monday 10:00 UTC (after AGT-14 at 09:00)
"""

import asyncio
import logging
import os
from typing import Any, Dict

import anthropic
from celery import Task

from backend.app.celery_app import celery_app
from backend.app.agents.analytics_agent import AnalyticsAgent
from backend.app.agents.replanning_agent import ReplanningAgent
from backend.app.agents.report_generator import ReportAgent
from backend.app.db import get_session_local
from backend.app.tasks.analytics_tasks import PlatformTool

logger = logging.getLogger(__name__)

_CHANNELS = ["google_ads", "meta_ads", "linkedin_ads"]


class AsyncTask(Task):
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        loop = asyncio.get_event_loop_policy().new_event_loop()
        try:
            return loop.run_until_complete(self.run(*args, **kwargs))
        finally:
            loop.close()


def _build_anthropic_client() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


@celery_app.task(
    name="reports.generate_daily_report",
    base=AsyncTask,
    bind=True,
)
async def generate_daily_report_task(self, mandate_id: str, tenant_id: str) -> Dict[str, Any]:
    """Daily 09:00 UTC — run AGT-13 then produce daily digest report.

    Args:
        mandate_id: Mandate identifier.
        tenant_id: Tenant identifier (multi-tenant isolation).

    Returns:
        Daily report dict.
    """
    logger.info("Starting daily report", extra={"mandate_id": mandate_id})
    try:
        SessionLocal = get_session_local()
        if SessionLocal is None:
            raise RuntimeError("SessionLocal factory not initialized")

        async with SessionLocal() as db_session:
            platform_tools = {ch: PlatformTool(db_session, ch) for ch in _CHANNELS}
            analytics_agent = AnalyticsAgent(db_session, platform_tools)
            analytics_summary = await analytics_agent.run_daily_analysis(mandate_id=mandate_id)

            anthropic_client = _build_anthropic_client()
            report_agent = ReportAgent(db_session, anthropic_client)
            report = await report_agent.run_daily(mandate_id, tenant_id, analytics_summary)

        logger.info("Daily report complete", extra={"mandate_id": mandate_id})
        return report

    except Exception as exc:
        logger.error("Daily report failed: %s", exc, extra={"mandate_id": mandate_id}, exc_info=True)
        raise


@celery_app.task(
    name="reports.generate_weekly_report",
    base=AsyncTask,
    bind=True,
)
async def generate_weekly_report_task(self, mandate_id: str, tenant_id: str) -> Dict[str, Any]:
    """Monday 10:00 UTC — run AGT-13 + AGT-14 then produce weekly full report.

    Args:
        mandate_id: Mandate identifier.
        tenant_id: Tenant identifier (multi-tenant isolation).

    Returns:
        Weekly report dict with trends and LLM narrative.
    """
    logger.info("Starting weekly report", extra={"mandate_id": mandate_id})
    try:
        SessionLocal = get_session_local()
        if SessionLocal is None:
            raise RuntimeError("SessionLocal factory not initialized")

        anthropic_client = _build_anthropic_client()

        async with SessionLocal() as db_session:
            platform_tools = {ch: PlatformTool(db_session, ch) for ch in _CHANNELS}
            analytics_agent = AnalyticsAgent(db_session, platform_tools)
            analytics_summary = await analytics_agent.run_daily_analysis(mandate_id=mandate_id)

            replan_agent = ReplanningAgent(anthropic_client)
            replan_recommendations = await replan_agent.run_weekly_replan(
                mandate_id=mandate_id,
                analytics_summary=analytics_summary,
                activation_plan={},
            )

            report_agent = ReportAgent(db_session, anthropic_client)
            report = await report_agent.run_weekly(
                mandate_id, tenant_id, analytics_summary, replan_recommendations
            )

        logger.info("Weekly report complete", extra={"mandate_id": mandate_id})
        return report

    except Exception as exc:
        logger.error("Weekly report failed: %s", exc, extra={"mandate_id": mandate_id}, exc_info=True)
        raise
```

- [ ] **Step 2: Verify import**

```bash
cd backend && python -c "from app.tasks.report_tasks import generate_daily_report_task, generate_weekly_report_task; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Run full test suite one final time**

```bash
cd backend && python -m pytest tests/agents/test_report_generator.py -v
```

Expected: `15 passed`

- [ ] **Step 4: Commit**

```bash
git add backend/app/tasks/report_tasks.py
git commit -m "[TASK-022] feat: add Celery report tasks for AGT-15 daily and weekly schedules"
```

---

## Completion Checklist

- [ ] `backend/app/models/report.py` — Report model with 2 composite indexes
- [ ] `backend/alembic/versions/2026_05_13_00_create_report_table.py` — Migration
- [ ] `backend/app/services/report_service.py` — save + get_latest, both tenant-scoped
- [ ] `backend/app/agents/report_generator.py` — 5 classes, 2 public methods on ReportAgent
- [ ] `backend/app/tasks/report_tasks.py` — daily + weekly Celery tasks
- [ ] `backend/tests/agents/test_report_generator.py` — 15 tests, all passing
