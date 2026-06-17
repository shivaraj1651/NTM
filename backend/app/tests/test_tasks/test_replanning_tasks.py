"""Tests for replanning_tasks.py — weekly replan Celery task."""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from backend.app.tasks.replanning_tasks import run_weekly_replan_task


class TestTaskRegistration:
    def test_task_registered(self):
        assert run_weekly_replan_task is not None

    def test_task_name(self):
        assert run_weekly_replan_task.name == "replanning.run_weekly_replan"


class TestRunWeeklyReplanTask:
    @pytest.mark.asyncio
    async def test_raises_when_session_local_not_initialized(self):
        with patch("backend.app.tasks.replanning_tasks.get_session_local", return_value=None):
            with pytest.raises(RuntimeError, match="SessionLocal factory not initialized"):
                await run_weekly_replan_task.run(str(UUID(int=2)))

    @pytest.mark.asyncio
    async def test_returns_recommendations_dict(self):
        fake_summary = {"activations": [], "red_alerts": [], "summary_by_channel": {}}
        fake_recommendations = [{"action": "shift_budget"}, {"action": "pause_creative"}]

        mock_session = AsyncMock()
        mock_db_cm = MagicMock()
        mock_db_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db_cm.__aexit__ = AsyncMock(return_value=None)
        mock_session_local = MagicMock(return_value=mock_db_cm)

        with patch("backend.app.tasks.replanning_tasks.get_session_local",
                   return_value=mock_session_local), \
             patch("backend.app.tasks.replanning_tasks.AnalyticsAgent") as mock_analytics_cls, \
             patch("backend.app.tasks.replanning_tasks.ReplanningAgent") as mock_replan_cls, \
             patch("backend.app.tasks.replanning_tasks.anthropic") as mock_anthropic:
            mock_analytics = AsyncMock()
            mock_analytics.run_daily_analysis = AsyncMock(return_value=fake_summary)
            mock_analytics_cls.return_value = mock_analytics

            mock_replan = AsyncMock()
            mock_replan.run_weekly_replan = AsyncMock(return_value=fake_recommendations)
            mock_replan_cls.return_value = mock_replan

            mock_anthropic.AsyncAnthropic.return_value = MagicMock()

            result = await run_weekly_replan_task.run(str(UUID(int=2)))

        assert "recommendations" in result
        assert "count" in result
        assert result["count"] == len(fake_recommendations)
        assert result["recommendations"] == fake_recommendations
