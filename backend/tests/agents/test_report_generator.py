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
