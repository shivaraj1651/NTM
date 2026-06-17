"""Tests for report_tasks.py — daily and weekly report Celery tasks."""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from backend.app.tasks.report_tasks import (
    generate_daily_report_task,
    generate_weekly_report_task,
)


class TestTaskRegistration:
    def test_daily_report_task_registered(self):
        assert generate_daily_report_task is not None

    def test_weekly_report_task_registered(self):
        assert generate_weekly_report_task is not None

    def test_daily_report_task_name(self):
        assert generate_daily_report_task.name == "reports.generate_daily_report"

    def test_weekly_report_task_name(self):
        assert generate_weekly_report_task.name == "reports.generate_weekly_report"


class TestGenerateDailyReportTask:
    @pytest.mark.asyncio
    async def test_raises_when_session_local_not_initialized(self):
        with patch("backend.app.tasks.report_tasks.get_session_local", return_value=None):
            with pytest.raises(RuntimeError, match="SessionLocal factory not initialized"):
                await generate_daily_report_task.run(str(UUID(int=3)), "tenant-001")

    @pytest.mark.asyncio
    async def test_calls_analytics_and_report_agents(self):
        fake_summary = {"activations": [], "red_alerts": [], "summary_by_channel": {}}
        fake_report = {"type": "daily", "mandate_id": str(UUID(int=3)), "kpis": []}

        mock_session = AsyncMock()
        mock_db_cm = MagicMock()
        mock_db_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db_cm.__aexit__ = AsyncMock(return_value=None)
        mock_session_local = MagicMock(return_value=mock_db_cm)

        with patch("backend.app.tasks.report_tasks.get_session_local",
                   return_value=mock_session_local), \
             patch("backend.app.tasks.report_tasks.AnalyticsAgent") as mock_analytics_cls, \
             patch("backend.app.tasks.report_tasks.ReportAgent") as mock_report_cls, \
             patch("backend.app.tasks.report_tasks.anthropic") as mock_anthropic:
            mock_analytics = AsyncMock()
            mock_analytics.run_daily_analysis = AsyncMock(return_value=fake_summary)
            mock_analytics_cls.return_value = mock_analytics

            mock_report = AsyncMock()
            mock_report.run_daily = AsyncMock(return_value=fake_report)
            mock_report_cls.return_value = mock_report

            mock_anthropic.AsyncAnthropic.return_value = MagicMock()

            result = await generate_daily_report_task.run(str(UUID(int=3)), "tenant-001")

        assert result == fake_report
        mock_analytics.run_daily_analysis.assert_awaited_once()
        mock_report.run_daily.assert_awaited_once()


class TestGenerateWeeklyReportTask:
    @pytest.mark.asyncio
    async def test_raises_when_session_local_not_initialized(self):
        with patch("backend.app.tasks.report_tasks.get_session_local", return_value=None):
            with pytest.raises(RuntimeError, match="SessionLocal factory not initialized"):
                await generate_weekly_report_task.run(str(UUID(int=4)), "tenant-001")

    @pytest.mark.asyncio
    async def test_calls_analytics_replan_and_report_agents(self):
        fake_summary = {"activations": [], "red_alerts": [], "summary_by_channel": {}}
        fake_recommendations = [{"action": "reallocate"}]
        fake_report = {"type": "weekly", "mandate_id": str(UUID(int=4))}

        mock_session = AsyncMock()
        mock_db_cm = MagicMock()
        mock_db_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db_cm.__aexit__ = AsyncMock(return_value=None)
        mock_session_local = MagicMock(return_value=mock_db_cm)

        with patch("backend.app.tasks.report_tasks.get_session_local",
                   return_value=mock_session_local), \
             patch("backend.app.tasks.report_tasks.AnalyticsAgent") as mock_analytics_cls, \
             patch("backend.app.tasks.report_tasks.ReplanningAgent") as mock_replan_cls, \
             patch("backend.app.tasks.report_tasks.ReportAgent") as mock_report_cls, \
             patch("backend.app.tasks.report_tasks.anthropic") as mock_anthropic:
            mock_analytics = AsyncMock()
            mock_analytics.run_daily_analysis = AsyncMock(return_value=fake_summary)
            mock_analytics_cls.return_value = mock_analytics

            mock_replan = AsyncMock()
            mock_replan.run_weekly_replan = AsyncMock(
                return_value={"recommendations": fake_recommendations}
            )
            mock_replan_cls.return_value = mock_replan

            mock_report = AsyncMock()
            mock_report.run_weekly = AsyncMock(return_value=fake_report)
            mock_report_cls.return_value = mock_report

            mock_anthropic.AsyncAnthropic.return_value = MagicMock()

            result = await generate_weekly_report_task.run(str(UUID(int=4)), "tenant-001")

        assert result == fake_report
        mock_analytics.run_daily_analysis.assert_awaited_once()
        mock_replan.run_weekly_replan.assert_awaited_once()
        mock_report.run_weekly.assert_awaited_once()
