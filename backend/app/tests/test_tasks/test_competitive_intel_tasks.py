"""Tests for competitive_intel_tasks.py — competitor metrics and CI report tasks."""
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.tasks.competitive_intel_tasks import (
    fetch_competitor_metrics,
    get_competitor_cache,
    synthesize_competitive_report,
)


class TestTaskRegistration:
    def test_task_registered(self):
        assert fetch_competitor_metrics is not None

    def test_task_name_contains_function(self):
        assert "fetch_competitor_metrics" in fetch_competitor_metrics.name

    def test_task_max_retries(self):
        assert fetch_competitor_metrics.max_retries == 3


class TestGetCompetitorCache:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_cached_entry(self):
        mock_collection = AsyncMock()
        mock_collection.find_one = AsyncMock(return_value=None)
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        result = await get_competitor_cache(mock_db, "Nike", "tenant-001")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_cache_expired(self):
        old_ts = (datetime.now(UTC) - timedelta(days=10)).isoformat()
        mock_collection = AsyncMock()
        mock_collection.find_one = AsyncMock(return_value={
            "competitor_name": "Nike",
            "tenant_id": "tenant-001",
            "created_at": old_ts,
            "metrics": {"channels": {}, "messaging_themes": []},
        })
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        result = await get_competitor_cache(mock_db, "Nike", "tenant-001")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_metrics_when_fresh_cache(self):
        fresh_ts = datetime.now(UTC).isoformat()
        cached_metrics = {"channels": {"google_ads": {}}, "messaging_themes": ["performance"]}
        mock_collection = AsyncMock()
        mock_collection.find_one = AsyncMock(return_value={
            "competitor_name": "Nike",
            "tenant_id": "tenant-001",
            "created_at": fresh_ts,
            "metrics": cached_metrics,
        })
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        result = await get_competitor_cache(mock_db, "Nike", "tenant-001")

        assert result == cached_metrics


class TestSynthesizeCompetitiveReport:
    @pytest.mark.asyncio
    async def test_returns_fallback_on_llm_error(self):
        with patch("backend.app.tasks.competitive_intel_tasks.AsyncAnthropic") as mock_cls:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(
                side_effect=RuntimeError("API unreachable")
            )
            mock_cls.return_value = mock_client

            result = await synthesize_competitive_report(
                competitors_metrics=[{"channels": {}, "messaging_themes": []}],
                mandate={"campaign_concept": {}, "geography": {}, "budget": {}},
            )

        assert "untapped_channels" in result
        assert "market_concentration" in result
        assert result["market_concentration"] == "unknown"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_returns_fallback_on_empty_response(self):
        mock_response = MagicMock()
        mock_response.content = []

        with patch("backend.app.tasks.competitive_intel_tasks.AsyncAnthropic") as mock_cls:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_cls.return_value = mock_client

            result = await synthesize_competitive_report(
                competitors_metrics=[],
                mandate={},
            )

        assert result["market_concentration"] == "unknown"

    @pytest.mark.asyncio
    async def test_parses_valid_llm_response(self):
        valid_json = (
            '{"untapped_channels": ["podcast"], '
            '"messaging_gaps": ["sustainability"], '
            '"geographic_gaps": ["APAC"], '
            '"market_concentration": "fragmented"}'
        )
        mock_content = MagicMock()
        mock_content.text = valid_json
        mock_response = MagicMock()
        mock_response.content = [mock_content]

        with patch("backend.app.tasks.competitive_intel_tasks.AsyncAnthropic") as mock_cls, \
             patch("backend.app.tasks.competitive_intel_tasks.extract_json",
                   return_value={
                       "untapped_channels": ["podcast"],
                       "messaging_gaps": ["sustainability"],
                       "geographic_gaps": ["APAC"],
                       "market_concentration": "fragmented",
                   }):
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_cls.return_value = mock_client

            result = await synthesize_competitive_report(
                competitors_metrics=[],
                mandate={},
            )

        assert result["market_concentration"] == "fragmented"
        assert "podcast" in result["untapped_channels"]
