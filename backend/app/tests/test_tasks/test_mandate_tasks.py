"""Tests for mandate_tasks.py — AGT-01 mandate analysis Celery task."""
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.tasks.mandate_tasks import _run_mandate_analysis, run_mandate_analysis


class TestTaskRegistration:
    def test_task_registered(self):
        assert run_mandate_analysis is not None

    def test_task_name_contains_function(self):
        assert "run_mandate_analysis" in run_mandate_analysis.name

    def test_task_max_retries(self):
        assert run_mandate_analysis.max_retries == 3


class TestRunMandateAnalysisAsync:
    def _mock_factory(self, session):
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=session)
        cm.__aexit__ = AsyncMock(return_value=None)
        factory = MagicMock(return_value=cm)
        return factory

    @pytest.mark.asyncio
    async def test_exits_early_when_mandate_not_found(self):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("backend.app.tasks.mandate_tasks._make_engine") as mock_engine, \
             patch("backend.app.tasks.mandate_tasks.async_sessionmaker",
                   return_value=self._mock_factory(mock_session)), \
             patch("backend.app.tasks.mandate_tasks.mandate_analyst_agent") as mock_agent:
            mock_engine.return_value.dispose = AsyncMock()
            await _run_mandate_analysis("mandate-001", "tenant-001")

        mock_agent.assert_not_called()

    @pytest.mark.asyncio
    async def test_calls_agent_and_stores_to_mongo(self):
        mock_mandate = MagicMock()
        mock_mandate.to_dict.return_value = {"id": "mandate-001", "title": "Test"}
        mock_mandate.status = "pending"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_mandate
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        mock_collection = AsyncMock()
        mock_collection.insert_one = AsyncMock()
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        mock_motor = MagicMock()
        mock_motor.__getitem__ = MagicMock(return_value=mock_db)
        mock_motor.close = MagicMock()

        mock_ci_module = MagicMock()

        with patch("backend.app.tasks.mandate_tasks._make_engine") as mock_engine, \
             patch("backend.app.tasks.mandate_tasks.async_sessionmaker",
                   return_value=self._mock_factory(mock_session)), \
             patch("backend.app.tasks.mandate_tasks.mandate_analyst_agent",
                   new=AsyncMock(return_value={"analysis": "done"})), \
             patch("backend.app.tasks.mandate_tasks.AsyncIOMotorClient",
                   return_value=mock_motor), \
             patch.dict(sys.modules,
                        {"backend.app.tasks.competitive_intel_tasks": mock_ci_module}):
            mock_engine.return_value.dispose = AsyncMock()
            await _run_mandate_analysis("mandate-001", "tenant-001")

        mock_collection.insert_one.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_dispatches_ci_pipeline_after_success(self):
        mock_mandate = MagicMock()
        mock_mandate.to_dict.return_value = {"id": "mandate-002"}
        mock_mandate.status = "pending"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_mandate
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        mock_collection = AsyncMock()
        mock_collection.insert_one = AsyncMock()
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        mock_motor = MagicMock()
        mock_motor.__getitem__ = MagicMock(return_value=mock_db)
        mock_motor.close = MagicMock()

        mock_ci_pipeline = MagicMock()
        mock_ci_module = MagicMock()
        mock_ci_module.run_competitive_intel_pipeline = mock_ci_pipeline

        with patch("backend.app.tasks.mandate_tasks._make_engine") as mock_engine, \
             patch("backend.app.tasks.mandate_tasks.async_sessionmaker",
                   return_value=self._mock_factory(mock_session)), \
             patch("backend.app.tasks.mandate_tasks.mandate_analyst_agent",
                   new=AsyncMock(return_value={"analysis": "done"})), \
             patch("backend.app.tasks.mandate_tasks.AsyncIOMotorClient",
                   return_value=mock_motor), \
             patch.dict(sys.modules,
                        {"backend.app.tasks.competitive_intel_tasks": mock_ci_module}):
            mock_engine.return_value.dispose = AsyncMock()
            await _run_mandate_analysis("mandate-002", "tenant-001")

        mock_ci_pipeline.delay.assert_called_once_with("mandate-002", "tenant-001")
