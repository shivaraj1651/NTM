import pytest
from uuid import uuid4
from unittest.mock import patch, AsyncMock
from backend.app.tools.google_ads import activate_google


@pytest.mark.asyncio
async def test_activate_google_success():
    """Test successful Google Ads campaign activation."""
    activation = {
        "id": str(uuid4()),
        "cost_estimated": 5000.0,
        "estimated_reach": 50000,
        "audience_segment": "brand_aware",
        "geography": "US",
        "format": "Video 15s"
    }

    platform_config = {
        "age_min": 18,
        "age_max": 65,
        "interests": ["technology"]
    }

    creative_url = "https://example.com/creative.mp4"

    with patch('backend.app.tools.google_ads.httpx.AsyncClient') as mock_client_class:
        # Mock first response (campaign creation)
        mock_response = AsyncMock()
        mock_response.json = lambda: {
            "id": "camps_123456",
            "resourceName": "customers/1234567890/campaigns/1234567890"
        }
        mock_response.raise_for_status = lambda: None

        # Mock second response (ad creation)
        mock_ad_response = AsyncMock()
        mock_ad_response.json = lambda: {"id": "ads_789"}
        mock_ad_response.raise_for_status = lambda: None

        # Setup context manager and post method
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[mock_response, mock_ad_response])
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result = await activate_google(
            activation=activation,
            platform_config=platform_config,
            creative_url=creative_url
        )

        assert result["campaign_id"] == "camps_123456"
        assert result["ad_id"] == "ads_789"
        assert result["status"] == "live"
        assert result["error"] is None


@pytest.mark.asyncio
async def test_activate_google_api_failure():
    """Test handling API failure gracefully."""
    activation = {"id": str(uuid4())}
    platform_config = {}
    creative_url = "https://example.com/creative.mp4"

    with patch('backend.app.tools.google_ads.httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post.side_effect = Exception("API Error")

        result = await activate_google(
            activation=activation,
            platform_config=platform_config,
            creative_url=creative_url
        )

        assert result["status"] == "failed"
        assert "API Error" in result["error"]


@pytest.mark.asyncio
async def test_activate_google_returns_dict_with_required_fields():
    """Test that activate_google always returns required fields."""
    activation = {"id": str(uuid4())}
    platform_config = {}
    creative_url = "https://example.com/creative.mp4"

    with patch('backend.app.tools.google_ads.httpx.AsyncClient') as mock_client_class:
        # Mock first response (campaign creation)
        mock_response = AsyncMock()
        mock_response.json = lambda: {"id": "camps_789"}
        mock_response.raise_for_status = lambda: None

        # Mock second response (ad creation)
        mock_ad_response = AsyncMock()
        mock_ad_response.json = lambda: {"id": "ads_999"}
        mock_ad_response.raise_for_status = lambda: None

        # Setup context manager and post method
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[mock_response, mock_ad_response])
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result = await activate_google(activation, platform_config, creative_url)

        # Result must have these keys
        assert "campaign_id" in result
        assert "ad_id" in result
        assert "status" in result
        assert "error" in result
