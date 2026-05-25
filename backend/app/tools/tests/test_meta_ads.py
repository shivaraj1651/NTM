import pytest
import os
from uuid import uuid4
from unittest.mock import patch, AsyncMock
from backend.app.tools.meta_ads import activate_meta, _get_access_token


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
