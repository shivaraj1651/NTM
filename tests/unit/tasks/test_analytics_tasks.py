"""Tests for analytics Celery tasks.

Tests the run_daily_analytics_task wrapper that schedules AnalyticsAgent.
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock
from backend.app.tasks.analytics_tasks import run_daily_analytics_task


@pytest.mark.asyncio
async def test_run_daily_analytics_task():
    """Test Celery task wrapper for daily analytics."""
    with patch("backend.app.tasks.analytics_tasks.AnalyticsAgent") as mock_agent_class:
        with patch("backend.app.tasks.analytics_tasks.get_session_local") as mock_get_session:
            mock_agent = AsyncMock()
            mock_agent.run_daily_analysis.return_value = {
                "mandate_id": "test",
                "activations": []
            }
            mock_agent_class.return_value = mock_agent

            # Mock SessionLocal factory - needs to be an async context manager
            mock_session = MagicMock()

            class AsyncContextManagerMock:
                async def __aenter__(self):
                    return mock_session

                async def __aexit__(self, *args):
                    pass

                def __call__(self):
                    return self

            mock_session_factory = AsyncContextManagerMock()
            mock_get_session.return_value = mock_session_factory

            # Call the async task function directly (not through Celery wrapper)
            test_mandate_id = str(uuid4())
            result = await run_daily_analytics_task.run(mandate_id=test_mandate_id)
            assert result is not None
            assert "activations" in result
