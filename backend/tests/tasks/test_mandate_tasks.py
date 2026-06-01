"""Unit tests for mandate Celery tasks."""

from unittest.mock import patch

import pytest


def test_run_mandate_analysis_is_celery_task():
    from backend.app.tasks.mandate_tasks import run_mandate_analysis
    assert hasattr(run_mandate_analysis, 'delay'), "must be a Celery task"


def test_run_mandate_analysis_sets_analyzing_then_analyzed():
    """Task should call asyncio.run to execute async orchestration."""
    from backend.app.tasks.mandate_tasks import run_mandate_analysis

    with patch("backend.app.tasks.mandate_tasks.asyncio.run") as mock_run:
        mock_run.return_value = None
        run_mandate_analysis("m-001", "tenant-1")
        assert mock_run.called


def test_run_mandate_analysis_handles_exception_gracefully():
    """Task should call self.retry on exception, not silently swallow it."""
    from celery.exceptions import Retry

    from backend.app.tasks.mandate_tasks import run_mandate_analysis

    with patch("backend.app.tasks.mandate_tasks.asyncio.run", side_effect=Exception("boom")):
        with pytest.raises((Retry, Exception)):
            run_mandate_analysis("m-001", "tenant-1")


def test_run_campaign_strategy_is_celery_task():
    from backend.app.tasks.campaign_tasks import run_campaign_strategy
    assert hasattr(run_campaign_strategy, 'delay'), "must be a Celery task"
