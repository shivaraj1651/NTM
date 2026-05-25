import pytest
import os
import httpx
from uuid import uuid4
from unittest.mock import patch, AsyncMock
from backend.app.tools.meta_ads import activate_meta, _get_access_token, create_campaign, create_ad_set, create_ad, get_ad_insights, pause_ad, update_ad_budget


def _mock_post_response(response_id: str):
    m = AsyncMock()
    m.json = lambda: {"id": response_id}
    m.raise_for_status = lambda: None
    return m


@pytest.mark.asyncio
async def test_activate_meta_success():
    """Test successful Meta campaign activation."""
    activation = {
        "id": str(uuid4()),
        "cost_estimated": 5000.0,
        "estimated_reach": 100000,
        "audience_segment": "consideration",
        "geography": "US",
        "format": "Static Image"
    }

    platform_config = {
        "age_min": 25,
        "age_max": 55,
        "interests": ["business"],
        "device": "mobile"
    }

    creative_url = "https://example.com/image.jpg"

    with patch('backend.app.tools.meta_ads.httpx.AsyncClient') as mock_client_class:
        # Mock three responses for campaign, adset, and ad creation
        mock_campaign_response = AsyncMock()
        mock_campaign_response.json = lambda: {"id": "123456789"}
        mock_campaign_response.raise_for_status = lambda: None

        mock_adset_response = AsyncMock()
        mock_adset_response.json = lambda: {"id": "987654321"}
        mock_adset_response.raise_for_status = lambda: None

        mock_ad_response = AsyncMock()
        mock_ad_response.json = lambda: {"id": "111222333"}
        mock_ad_response.raise_for_status = lambda: None

        # Setup context manager and post method
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[mock_campaign_response, mock_adset_response, mock_ad_response])
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result = await activate_meta(
            activation=activation,
            platform_config=platform_config,
            creative_url=creative_url
        )

        assert result["campaign_id"] == "123456789"
        assert result["ad_id"] == "111222333"
        assert result["status"] == "live"
        assert result["error"] is None


@pytest.mark.asyncio
async def test_activate_meta_api_failure():
    """Test handling API failure gracefully."""
    activation = {"id": str(uuid4())}
    platform_config = {}
    creative_url = "https://example.com/image.jpg"

    with patch('backend.app.tools.meta_ads.httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post.side_effect = Exception("Network error")

        result = await activate_meta(
            activation=activation,
            platform_config=platform_config,
            creative_url=creative_url
        )

        assert result["status"] == "failed"
        assert "Network error" in result["error"]


@pytest.mark.asyncio
async def test_activate_meta_returns_required_fields():
    """Test that activate_meta always returns required fields."""
    activation = {"id": str(uuid4())}
    platform_config = {}
    creative_url = "https://example.com/image.jpg"

    with patch('backend.app.tools.meta_ads.httpx.AsyncClient') as mock_client_class:
        # Mock three responses for campaign, adset, and ad creation
        mock_campaign_response = AsyncMock()
        mock_campaign_response.json = lambda: {"id": "123"}
        mock_campaign_response.raise_for_status = lambda: None

        mock_adset_response = AsyncMock()
        mock_adset_response.json = lambda: {"id": "456"}
        mock_adset_response.raise_for_status = lambda: None

        mock_ad_response = AsyncMock()
        mock_ad_response.json = lambda: {"id": "789"}
        mock_ad_response.raise_for_status = lambda: None

        # Setup context manager and post method
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[mock_campaign_response, mock_adset_response, mock_ad_response])
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result = await activate_meta(activation, platform_config, creative_url)

        # Result must have these keys
        assert "campaign_id" in result
        assert "ad_id" in result
        assert "status" in result
        assert "error" in result


@pytest.mark.asyncio
async def test_missing_token_raises():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(RuntimeError, match="META_SYSTEM_USER_TOKEN must be set"):
            _get_access_token()


@pytest.mark.asyncio
async def test_create_campaign_success():
    with patch.dict(os.environ, {"META_SYSTEM_USER_TOKEN": "test-token"}), \
         patch("backend.app.tools.meta_ads.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_mock_post_response("camp_001"))
        mock_cls.return_value.__aenter__.return_value = mock_client

        result = await create_campaign(
            ad_account_id="123456789",
            name="Test Campaign",
            objective="LINK_CLICKS",
            budget=100.0,
            schedule={"start_time": 1700000000},
        )

    assert result == "camp_001"


@pytest.mark.asyncio
async def test_create_campaign_raises_on_http_error():
    with patch.dict(os.environ, {"META_SYSTEM_USER_TOKEN": "test-token"}), \
         patch("backend.app.tools.meta_ads.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.HTTPStatusError(
            "400 Bad Request", request=AsyncMock(), response=AsyncMock()
        )
        mock_cls.return_value.__aenter__.return_value = mock_client

        with pytest.raises(httpx.HTTPStatusError):
            await create_campaign(
                ad_account_id="123456789",
                name="Bad Campaign",
                objective="LINK_CLICKS",
                budget=100.0,
                schedule={},
            )


@pytest.mark.asyncio
async def test_create_ad_set_success():
    with patch.dict(os.environ, {
        "META_SYSTEM_USER_TOKEN": "test-token",
        "META_AD_ACCOUNT_ID": "999888777",
    }), patch("backend.app.tools.meta_ads.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_mock_post_response("adset_042"))
        mock_cls.return_value.__aenter__.return_value = mock_client

        result = await create_ad_set(
            campaign_id="camp_001",
            name="Test AdSet",
            audience_spec={"age_min": 25, "age_max": 54, "geo_locations": {"countries": ["US"]}},
            placements=["FACEBOOK_FEED", "INSTAGRAM_FEED"],
            budget=50.0,
        )

    assert result == "adset_042"


@pytest.mark.asyncio
async def test_create_ad_success():
    with patch.dict(os.environ, {
        "META_SYSTEM_USER_TOKEN": "test-token",
        "META_AD_ACCOUNT_ID": "999888777",
        "META_PAGE_ID": "111000222",
    }), patch("backend.app.tools.meta_ads.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_mock_post_response("ad_007"))
        mock_cls.return_value.__aenter__.return_value = mock_client

        result = await create_ad(
            ad_set_id="adset_042",
            creative_spec={
                "image_hash": "abc123",
                "link": "https://example.com",
                "message": "Check this out!",
            },
            name="Test Ad",
        )

    assert result == "ad_007"


@pytest.mark.asyncio
async def test_get_ad_insights_success():
    mock_insights_data = {
        "data": [{"impressions": "5000", "clicks": "120", "spend": "45.50"}],
        "paging": {}
    }

    with patch.dict(os.environ, {"META_SYSTEM_USER_TOKEN": "test-token"}), \
         patch("backend.app.tools.meta_ads.httpx.AsyncClient") as mock_cls:

        mock_get_response = AsyncMock()
        mock_get_response.json = lambda: mock_insights_data
        mock_get_response.raise_for_status = lambda: None

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_get_response)
        mock_cls.return_value.__aenter__.return_value = mock_client

        result = await get_ad_insights(
            ad_id="ad_007",
            date_range={"since": "2026-05-01", "until": "2026-05-25"},
            metrics_list=["impressions", "clicks", "spend"],
        )

    assert result["ad_id"] == "ad_007"
    assert "metrics" in result
    assert result["metrics"]["impressions"] == "5000"
    assert result["metrics"]["clicks"] == "120"


def _mock_bool_response():
    m = AsyncMock()
    m.json = lambda: {"success": True}
    m.raise_for_status = lambda: None
    return m


@pytest.mark.asyncio
async def test_pause_ad_returns_true():
    with patch.dict(os.environ, {"META_SYSTEM_USER_TOKEN": "test-token"}), \
         patch("backend.app.tools.meta_ads.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_mock_bool_response())
        mock_cls.return_value.__aenter__.return_value = mock_client

        result = await pause_ad(ad_id="ad_007")

    assert result is True


@pytest.mark.asyncio
async def test_update_ad_budget_returns_true():
    with patch.dict(os.environ, {"META_SYSTEM_USER_TOKEN": "test-token"}), \
         patch("backend.app.tools.meta_ads.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_mock_bool_response())
        mock_cls.return_value.__aenter__.return_value = mock_client

        result = await update_ad_budget(ad_set_id="adset_042", daily_budget=75.0)

    assert result is True
