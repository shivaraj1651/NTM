"""Tests for campaign_tasks.py — campaign pipeline Celery tasks."""
from unittest.mock import MagicMock, patch

import pytest

from backend.app.tasks.campaign_tasks import (
    poll_kling_video,
    run_budget_optimization,
    run_campaign_strategy,
    run_concept_generation,
    run_creative_generation,
    run_media_planning,
    run_video_generation,
)


class TestTaskRegistration:
    def test_run_campaign_strategy_registered(self):
        assert run_campaign_strategy is not None

    def test_run_concept_generation_registered(self):
        assert run_concept_generation is not None

    def test_run_media_planning_registered(self):
        assert run_media_planning is not None

    def test_run_video_generation_registered(self):
        assert run_video_generation is not None

    def test_poll_kling_video_registered(self):
        assert poll_kling_video is not None

    def test_run_budget_optimization_registered(self):
        assert run_budget_optimization is not None

    def test_run_creative_generation_registered(self):
        assert run_creative_generation is not None


class TestTaskNamingConvention:
    def test_all_names_contain_function_name(self):
        tasks_and_names = [
            (run_campaign_strategy, "run_campaign_strategy"),
            (run_concept_generation, "run_concept_generation"),
            (run_media_planning, "run_media_planning"),
            (run_video_generation, "run_video_generation"),
            (poll_kling_video, "poll_kling_video"),
            (run_budget_optimization, "run_budget_optimization"),
            (run_creative_generation, "run_creative_generation"),
        ]
        for task, expected_fragment in tasks_and_names:
            assert expected_fragment in task.name, (
                f"Expected '{expected_fragment}' in task name '{task.name}'"
            )


class TestRetryConfiguration:
    def test_run_campaign_strategy_max_retries(self):
        assert run_campaign_strategy.max_retries == 3

    def test_run_concept_generation_max_retries(self):
        assert run_concept_generation.max_retries == 2

    def test_run_media_planning_max_retries(self):
        assert run_media_planning.max_retries == 3

    def test_run_video_generation_max_retries(self):
        assert run_video_generation.max_retries == 2

    def test_poll_kling_video_max_retries(self):
        assert poll_kling_video.max_retries == 8

    def test_run_budget_optimization_max_retries(self):
        assert run_budget_optimization.max_retries == 3

    def test_run_creative_generation_max_retries(self):
        assert run_creative_generation.max_retries == 2


class TestRunCampaignStrategy:
    def test_strategy_calls_asyncio_run(self):
        with patch("backend.app.tasks.campaign_tasks.asyncio.run") as mock_run:
            mock_run.return_value = None
            run_campaign_strategy.run(mandate_id="mand-001", tenant_id="ten-001")

        mock_run.assert_called_once()

    def test_strategy_retries_on_exception(self):
        mock_self = MagicMock()
        mock_self.request.retries = 0
        mock_self.retry = MagicMock(side_effect=Exception("retry"))

        with patch("backend.app.tasks.campaign_tasks.asyncio.run",
                   side_effect=RuntimeError("DB down")):
            with pytest.raises(Exception):
                run_campaign_strategy.__wrapped__(
                    mock_self, mandate_id="mand-001", tenant_id="ten-001"
                ) if hasattr(run_campaign_strategy, "__wrapped__") else \
                run_campaign_strategy.run.__func__(
                    mock_self, mandate_id="mand-001", tenant_id="ten-001"
                )
