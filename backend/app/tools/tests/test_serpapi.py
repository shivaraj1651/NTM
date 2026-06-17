"""Tests for the SerpAPI tool (competitor search + brand info helpers)."""
import os
from unittest.mock import AsyncMock, patch

import pytest

from backend.app.tools.serpapi import (
    _extract_channels_from_result,
    _extract_messaging_themes,
    search_brand_info,
    search_competitor_ads,
)

_ORGANIC = [
    {"snippet": "Google Ads and Facebook ads are the top channels for performance marketing."},
    {"snippet": "LinkedIn campaign drives B2B leads with performance and speed."},
]

_SERP_RESPONSE = {
    "organic_results": _ORGANIC,
    "search_information": {"total_results": 1_500_000},
}


# ---------------------------------------------------------------------------
# Pure helper unit tests
# ---------------------------------------------------------------------------

def test_extract_channels_google_ads():
    assert "google_ads" in _extract_channels_from_result("They run google ads and search ads heavily.")


def test_extract_channels_facebook():
    assert "facebook" in _extract_channels_from_result("Meta ads and instagram ads are key.")


def test_extract_channels_linkedin():
    assert "linkedin" in _extract_channels_from_result("LinkedIn campaign targeting executives.")


def test_extract_channels_multiple():
    text = "google adwords, facebook ads, tiktok ads, and youtube advertising all in one plan."
    channels = _extract_channels_from_result(text)
    assert "google_ads" in channels
    assert "facebook" in channels
    assert "tiktok" in channels
    assert "youtube" in channels


def test_extract_channels_none_match():
    assert _extract_channels_from_result("print billboard newspaper TV") == []


def test_extract_messaging_performance():
    assert "performance" in _extract_messaging_themes(["blazing fast speed and efficiency"])


def test_extract_messaging_sustainability():
    assert "sustainability" in _extract_messaging_themes(["eco-friendly sustainable materials"])


def test_extract_messaging_empty():
    assert _extract_messaging_themes([]) == []


def test_extract_messaging_deduplicates():
    snippets = ["fast speed performance", "performance again"]
    themes = _extract_messaging_themes(snippets)
    assert themes.count("performance") == 1


# ---------------------------------------------------------------------------
# search_competitor_ads
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_competitor_ads_no_key_returns_error():
    with patch("backend.app.tools.serpapi.SERPAPI_API_KEY", None):
        result = await search_competitor_ads("Coca-Cola")
    assert result["channels_detected"] == []
    assert result["num_results"] == 0
    assert result["error"] is not None


@pytest.mark.asyncio
async def test_search_competitor_ads_success():
    with patch("backend.app.tools.serpapi.SERPAPI_API_KEY", "srp-key"), \
         patch("backend.app.tools.serpapi.httpx.AsyncClient") as mock_cls:

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = lambda: _SERP_RESPONSE
        mock_response.raise_for_status = lambda: None
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_cls.return_value.__aenter__.return_value = mock_client

        result = await search_competitor_ads("Nike", year=2026)

    assert result["num_results"] == len(_ORGANIC)
    assert isinstance(result["channels_detected"], list)
    assert isinstance(result["messaging_samples"], list)
    assert "error" not in result or result.get("error") is None


@pytest.mark.asyncio
async def test_search_competitor_ads_http_error_returns_error_dict():
    import httpx

    with patch("backend.app.tools.serpapi.SERPAPI_API_KEY", "srp-key"), \
         patch("backend.app.tools.serpapi.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.HTTPError("connection reset")
        mock_cls.return_value.__aenter__.return_value = mock_client

        result = await search_competitor_ads("Pepsi")

    assert result["num_results"] == 0
    assert "error" in result


@pytest.mark.asyncio
async def test_search_competitor_ads_includes_search_volume():
    with patch("backend.app.tools.serpapi.SERPAPI_API_KEY", "srp-key"), \
         patch("backend.app.tools.serpapi.httpx.AsyncClient") as mock_cls:

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = lambda: _SERP_RESPONSE
        mock_response.raise_for_status = lambda: None
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_cls.return_value.__aenter__.return_value = mock_client

        result = await search_competitor_ads("Adidas")

    assert result["estimated_search_volume"] == 1_500_000


# ---------------------------------------------------------------------------
# search_brand_info
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_brand_info_no_key_returns_empty_data():
    with patch("backend.app.tools.serpapi.SERPAPI_API_KEY", None):
        result = await search_brand_info("Samsung")
    assert result["taglines"] == []
    assert result["products"] == []
    assert result["raw_snippets"] == []


@pytest.mark.asyncio
async def test_search_brand_info_success():
    brand_response = {
        "organic_results": [
            {"snippet": '"Think Different" — the iconic Apple slogan.'},
            {"snippet": "Apple sells the iPhone, MacBook, and iPad product lines."},
        ]
    }

    with patch("backend.app.tools.serpapi.SERPAPI_API_KEY", "srp-key"), \
         patch("backend.app.tools.serpapi.httpx.AsyncClient") as mock_cls:

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = lambda: brand_response
        mock_response.raise_for_status = lambda: None
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_cls.return_value.__aenter__.return_value = mock_client

        result = await search_brand_info("Apple")

    assert "taglines" in result
    assert "products" in result
    assert "logo_hint" in result
    assert "recent_campaigns" in result
    assert "raw_snippets" in result
    assert "Apple" in result["logo_hint"]
