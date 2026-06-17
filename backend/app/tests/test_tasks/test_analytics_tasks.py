"""Tests for analytics_tasks.py — daily analytics Celery task."""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from backend.app.tasks.analytics_tasks import PlatformTool, run_daily_analytics_task


class TestTaskRegistration:
    def test_task_registered(self):
        assert run_daily_analytics_task is not None

    def test_task_name(self):
        assert run_daily_analytics_task.name == "analytics.run_daily_analysis"


class TestPlatformTool:
    @pytest.mark.asyncio
    async def test_get_metrics_returns_zeros_in_production_mode(self):
        """Production mode returns zeroed metrics (no real API calls in tests)."""
        db_session = AsyncMock()
        tool = PlatformTool(db_session, "google_ads")

        with patch("os.getenv", side_effect=lambda k, d=None: "0" if k == "NTM_ADS_TEST_MODE" else d):
            result = await tool.get_metrics({"id": "act-001", "channel": "google_ads"})

        assert result is not None
        assert "impressions" in result

    @pytest.mark.asyncio
    async def test_get_metrics_test_mode_generates_synthetic_metrics(self):
        import os
        tool = PlatformTool(AsyncMock(), "google_ads")

        with patch.dict(os.environ, {"NTM_ADS_TEST_MODE": "1"}):
            result = await tool.get_metrics({
                "id": "act-001",
                "channel": "google_ads",
                "estimated_reach": 100_000,
                "cost_estimated": 5_000,
            })

        assert result["impressions"] > 0
        assert result["clicks"] > 0
        assert "ctr" in result
        assert "roas" in result


class TestRunDailyAnalyticsTask:
    @pytest.mark.asyncio
    async def test_raises_when_session_local_not_initialized(self):
        with patch("backend.app.tasks.analytics_tasks.get_session_local", return_value=None):
            with pytest.raises(RuntimeError, match="SessionLocal factory not initialized"):
                await run_daily_analytics_task.run(str(UUID(int=1)))

    @pytest.mark.asyncio
    async def test_calls_agent_and_returns_summary(self):
        fake_summary = {
            "activations": [{"id": "act-001"}],
            "red_alerts": [],
            "summary_by_channel": {"google_ads": {}},
        }

        mock_session = AsyncMock()
        mock_db_cm = MagicMock()
        mock_db_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db_cm.__aexit__ = AsyncMock(return_value=None)
        mock_session_local = MagicMock(return_value=mock_db_cm)

        with patch("backend.app.tasks.analytics_tasks.get_session_local",
                   return_value=mock_session_local), \
             patch("backend.app.tasks.analytics_tasks.AnalyticsAgent") as mock_agent_cls:
            mock_agent = AsyncMock()
            mock_agent.run_daily_analysis = AsyncMock(return_value=fake_summary)
            mock_agent_cls.return_value = mock_agent

            result = await run_daily_analytics_task.run(str(UUID(int=1)))

        assert result == fake_summary
        mock_agent.run_daily_analysis.assert_awaited_once()
