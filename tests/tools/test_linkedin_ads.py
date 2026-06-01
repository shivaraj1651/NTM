"""Tests for LinkedIn Ads activation tool."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from backend.app.tools.linkedin_ads import activate_linkedin


@pytest.mark.asyncio
async def test_activate_linkedin_success():
    """Test successful LinkedIn campaign activation."""
    activation = {
        "id": str(uuid4()),
        "cost_estimated": 3000.0,
        "estimated_reach": 30000,
        "audience_segment": "brand_aware",
        "geography": "US",
        "format": "Static Image",
        "name": "B2B Tech Campaign"
    }

    platform_config = {
        "seniority": ["director", "c_level"],
        "job_title": ["marketing", "business"],
        "industries": ["technology"]
    }

    creative_url = "https://example.com/linkedin-image.jpg"

    with patch('backend.app.tools.linkedin_ads.httpx.AsyncClient') as mock_client:
        # Setup mock response for campaign creation
        mock_campaign_response = AsyncMock()
        mock_campaign_response.json = lambda: {
            "id": "urn:li:sponsoredCampaign:123456",
            "adId": "urn:li:sponsoredCreative:789012"
        }
        mock_campaign_response.raise_for_status = lambda: None

        # Setup mock response for creative creation
        mock_creative_response = AsyncMock()
        mock_creative_response.json = lambda: {
            "id": "urn:li:sponsoredCreative:789012"
        }
        mock_creative_response.raise_for_status = lambda: None

        # Setup async client mock
        mock_client.return_value.__aenter__.return_value.post.side_effect = [
            mock_campaign_response,
            mock_creative_response
        ]

        result = await activate_linkedin(
            activation=activation,
            platform_config=platform_config,
            creative_url=creative_url
        )

        assert "123456" in result["campaign_id"]
        assert result["status"] == "live"


@pytest.mark.asyncio
async def test_activate_linkedin_failure():
    """Test LinkedIn activation failure handling."""
    activation = {"id": str(uuid4()), "name": "Failed Campaign"}
    platform_config = {}
    creative_url = "https://example.com/image.jpg"

    with patch('backend.app.tools.linkedin_ads.httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post.side_effect = Exception("Auth failed")

        result = await activate_linkedin(
            activation=activation,
            platform_config=platform_config,
            creative_url=creative_url
        )

        assert result["status"] == "failed"
        assert "Auth failed" in result["error"]


@pytest.mark.asyncio
async def test_activate_linkedin_returns_required_fields():
    """Test that activate_linkedin returns required fields."""
    activation = {"id": str(uuid4()), "name": "Test Campaign"}
    platform_config = {}
    creative_url = "https://example.com/image.jpg"

    with patch('backend.app.tools.linkedin_ads.httpx.AsyncClient') as mock_client:
        # Setup mock response for campaign creation
        mock_campaign_response = AsyncMock()
        mock_campaign_response.json = lambda: {
            "id": "urn:li:sponsoredCampaign:999"
        }
        mock_campaign_response.raise_for_status = lambda: None

        # Setup mock response for creative creation
        mock_creative_response = AsyncMock()
        mock_creative_response.json = lambda: {
            "id": "urn:li:sponsoredCreative:888"
        }
        mock_creative_response.raise_for_status = lambda: None

        mock_client.return_value.__aenter__.return_value.post.side_effect = [
            mock_campaign_response,
            mock_creative_response
        ]

        result = await activate_linkedin(activation, platform_config, creative_url)

        assert "campaign_id" in result
        assert "ad_id" in result
        assert "status" in result
        assert "error" in result


@pytest.mark.asyncio
async def test_activate_linkedin_with_full_targeting():
    """Test LinkedIn activation with comprehensive B2B targeting."""
    activation = {
        "id": str(uuid4()),
        "name": "Enterprise Software Campaign",
        "cost_estimated": 5000.0,
    }

    platform_config = {
        "seniority": ["c_level", "director", "manager"],
        "job_title": ["cto", "cfo", "marketing_director"],
        "industries": ["technology", "financial_services", "manufacturing"],
        "locations": ["US", "CA", "UK"]
    }

    creative_url = "https://example.com/enterprise-ad.jpg"

    with patch('backend.app.tools.linkedin_ads.httpx.AsyncClient') as mock_client:
        # Setup mock response for campaign creation
        mock_campaign_response = AsyncMock()
        mock_campaign_response.json = lambda: {
            "id": "urn:li:sponsoredCampaign:555"
        }
        mock_campaign_response.raise_for_status = lambda: None

        # Setup mock response for creative creation
        mock_creative_response = AsyncMock()
        mock_creative_response.json = lambda: {
            "id": "urn:li:sponsoredCreative:666"
        }
        mock_creative_response.raise_for_status = lambda: None

        mock_client.return_value.__aenter__.return_value.post.side_effect = [
            mock_campaign_response,
            mock_creative_response
        ]

        result = await activate_linkedin(activation, platform_config, creative_url)

        assert result["status"] == "live"
        assert result["campaign_id"] is not None
        assert result["ad_id"] is not None
        assert result["error"] is None


@pytest.mark.asyncio
async def test_activate_linkedin_handles_missing_optional_fields():
    """Test that LinkedIn activation handles missing optional targeting fields."""
    activation = {"id": str(uuid4()), "name": "Minimal Campaign"}
    platform_config = {}  # Empty config
    creative_url = "https://example.com/image.jpg"

    with patch('backend.app.tools.linkedin_ads.httpx.AsyncClient') as mock_client:
        # Setup mock response for campaign creation
        mock_campaign_response = AsyncMock()
        mock_campaign_response.json = lambda: {
            "id": "urn:li:sponsoredCampaign:222"
        }
        mock_campaign_response.raise_for_status = lambda: None

        # Setup mock response for creative creation
        mock_creative_response = AsyncMock()
        mock_creative_response.json = lambda: {
            "id": "urn:li:sponsoredCreative:333"
        }
        mock_creative_response.raise_for_status = lambda: None

        mock_client.return_value.__aenter__.return_value.post.side_effect = [
            mock_campaign_response,
            mock_creative_response
        ]

        result = await activate_linkedin(activation, platform_config, creative_url)

        assert result["status"] == "live"
        assert result["error"] is None
