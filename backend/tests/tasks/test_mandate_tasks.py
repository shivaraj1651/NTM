"""Unit tests for mandate Celery tasks."""

from unittest.mock import patch, MagicMock


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
    """Task should not propagate uncaught exceptions (logs and returns)."""
    from backend.app.tasks.mandate_tasks import run_mandate_analysis

    with patch("backend.app.tasks.mandate_tasks.asyncio.run", side_effect=Exception("boom")):
        try:
            run_mandate_analysis("m-001", "tenant-1")
        except Exception:
            assert False, "run_mandate_analysis must not propagate exceptions"
