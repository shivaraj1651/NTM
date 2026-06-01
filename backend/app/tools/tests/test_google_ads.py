import os
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from backend.app.tools.google_ads import activate_google


def _budget_response():
    m = AsyncMock()
    m.json = lambda: {"results": [{"resourceName": "customers/123/campaignBudgets/101"}]}
    m.raise_for_status = lambda: None
    return m


def _campaign_response():
    m = AsyncMock()
    m.json = lambda: {"results": [{"resourceName": "customers/123/campaigns/456"}]}
    m.raise_for_status = lambda: None
    return m


def _ad_group_response():
    m = AsyncMock()
    m.json = lambda: {"results": [{"resourceName": "customers/123/adGroups/789"}]}
    m.raise_for_status = lambda: None
    return m


def _ad_response():
    m = AsyncMock()
    m.json = lambda: {"results": [{"resourceName": "customers/123/adGroupAds/999"}]}
    m.raise_for_status = lambda: None
    return m


@pytest.mark.asyncio
async def test_activate_google_success():
    activation = {
        "id": str(uuid4()),
        "name": "Test Campaign",
        "cost_estimated": 5000.0,
        "geography": "US",
    }
    platform_config = {"age_min": 18, "age_max": 65, "interests": ["technology"]}
    creative_url = "https://example.com/creative.mp4"

    with patch("backend.app.tools.google_ads._get_access_token", return_value="tok"), \
         patch.dict(os.environ, {"GOOGLE_ADS_CUSTOMER_ID": "123", "GOOGLE_ADS_DEVELOPER_TOKEN": "dev"}), \
         patch("backend.app.tools.google_ads.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[
            _budget_response(), _campaign_response(), _ad_group_response(), _ad_response()
        ])
        mock_cls.return_value.__aenter__.return_value = mock_client

        result = await activate_google(
            activation=activation,
            platform_config=platform_config,
            creative_url=creative_url,
        )

    assert result["campaign_id"] == "456"
    assert result["ad_id"] == "999"
    assert result["status"] == "live"
    assert result["error"] is None


@pytest.mark.asyncio
async def test_activate_google_api_failure():
    activation = {"id": str(uuid4()), "name": "Test"}

    with patch("backend.app.tools.google_ads._get_access_token", return_value="tok"), \
         patch.dict(os.environ, {"GOOGLE_ADS_CUSTOMER_ID": "123", "GOOGLE_ADS_DEVELOPER_TOKEN": "dev"}), \
         patch("backend.app.tools.google_ads.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("API Error")
        mock_cls.return_value.__aenter__.return_value = mock_client

        result = await activate_google(
            activation=activation, platform_config={}, creative_url="https://example.com/c.mp4"
        )

    assert result["status"] == "failed"
    assert "API Error" in result["error"]
    assert result["campaign_id"] is None
    assert result["ad_id"] is None


@pytest.mark.asyncio
async def test_activate_google_returns_dict_with_required_fields():
    activation = {"id": str(uuid4()), "name": "Test"}

    with patch("backend.app.tools.google_ads._get_access_token", return_value="tok"), \
         patch.dict(os.environ, {"GOOGLE_ADS_CUSTOMER_ID": "123", "GOOGLE_ADS_DEVELOPER_TOKEN": "dev"}), \
         patch("backend.app.tools.google_ads.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[
            _budget_response(), _campaign_response(), _ad_group_response(), _ad_response()
        ])
        mock_cls.return_value.__aenter__.return_value = mock_client

        result = await activate_google(
            activation=activation, platform_config={}, creative_url="https://example.com/c.mp4"
        )

    for field in ("campaign_id", "ad_id", "status", "error"):
        assert field in result


@pytest.mark.asyncio
async def test_activate_google_missing_credentials_returns_failed():
    activation = {"id": str(uuid4()), "name": "Test"}

    with patch("backend.app.tools.google_ads._get_access_token",
               side_effect=RuntimeError("GOOGLE_ADS_CLIENT_ID, GOOGLE_ADS_CLIENT_SECRET, and GOOGLE_ADS_REFRESH_TOKEN must be set")):

        result = await activate_google(
            activation=activation, platform_config={}, creative_url="https://example.com/c.mp4"
        )

    assert result["status"] == "failed"
    assert result["error"] is not None
    assert result["campaign_id"] is None


@pytest.mark.asyncio
async def test_activate_google_sends_developer_token_header():
    activation = {"id": str(uuid4()), "name": "Test Campaign", "cost_estimated": 1000.0}

    with patch("backend.app.tools.google_ads._get_access_token", return_value="test-tok"), \
         patch.dict(os.environ, {"GOOGLE_ADS_CUSTOMER_ID": "123", "GOOGLE_ADS_DEVELOPER_TOKEN": "my-dev-token"}), \
         patch("backend.app.tools.google_ads.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[
            _budget_response(), _campaign_response(), _ad_group_response(), _ad_response()
        ])
        mock_cls.return_value.__aenter__.return_value = mock_client

        await activate_google(
            activation=activation, platform_config={}, creative_url="https://example.com/c.mp4"
        )

        assert mock_client.post.call_count == 4
        for call in mock_client.post.call_args_list:
            call_kwargs = call[1]
            assert call_kwargs["headers"]["developer-token"] == "my-dev-token"
            assert call_kwargs["headers"]["Authorization"] == "Bearer test-tok"


@pytest.mark.asyncio
async def test_activate_google_missing_customer_id_returns_failed():
    activation = {"id": str(uuid4()), "name": "Test"}

    with patch("backend.app.tools.google_ads._get_access_token", return_value="tok"), \
         patch.dict(os.environ, {"GOOGLE_ADS_CUSTOMER_ID": "", "GOOGLE_ADS_DEVELOPER_TOKEN": "dev"}):

        result = await activate_google(
            activation=activation,
            platform_config={},
            creative_url="https://example.com/c.mp4",
        )

    assert result["status"] == "failed"
    assert result["campaign_id"] is None
    assert "GOOGLE_ADS_CUSTOMER_ID" in result["error"]
