import os
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from backend.app.tools.linkedin_ads import activate_linkedin


def _group_response():
    m = AsyncMock()
    m.json = lambda: {"id": 111}
    m.raise_for_status = lambda: None
    return m


def _campaign_response():
    m = AsyncMock()
    m.json = lambda: {"id": 222}
    m.raise_for_status = lambda: None
    return m


def _creative_response():
    m = AsyncMock()
    m.json = lambda: {"id": 333}
    m.raise_for_status = lambda: None
    return m


@pytest.mark.asyncio
async def test_activate_linkedin_success():
    activation = {
        "id": str(uuid4()),
        "name": "Test Campaign",
        "cost_estimated": 3000.0,
    }
    platform_config = {
        "seniority": ["SENIOR"],
        "job_title": ["Software Engineer"],
        "industries": ["Technology"],
        "locations": ["US"],
    }
    creative_url = "https://example.com/creative.mp4"

    with patch("backend.app.tools.linkedin_ads._get_access_token", return_value="test-tok"), \
         patch.dict(os.environ, {"LINKEDIN_ACCOUNT_ID": "999"}), \
         patch("backend.app.tools.linkedin_ads.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[
            _group_response(), _campaign_response(), _creative_response()
        ])
        mock_cls.return_value.__aenter__.return_value = mock_client

        result = await activate_linkedin(
            activation=activation,
            platform_config=platform_config,
            creative_url=creative_url,
        )

    assert result["campaign_id"] == "222"
    assert result["ad_id"] == "333"
    assert result["status"] == "live"
    assert result["error"] is None


@pytest.mark.asyncio
async def test_activate_linkedin_api_failure():
    activation = {"id": str(uuid4()), "name": "Test"}

    with patch("backend.app.tools.linkedin_ads._get_access_token", return_value="test-tok"), \
         patch.dict(os.environ, {"LINKEDIN_ACCOUNT_ID": "999"}), \
         patch("backend.app.tools.linkedin_ads.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("API Error")
        mock_cls.return_value.__aenter__.return_value = mock_client

        result = await activate_linkedin(
            activation=activation, platform_config={}, creative_url="https://example.com/c.mp4"
        )

    assert result["status"] == "failed"
    assert result["campaign_id"] is None
    assert result["ad_id"] is None
    assert "API Error" in result["error"]


@pytest.mark.asyncio
async def test_activate_linkedin_returns_required_fields():
    activation = {"id": str(uuid4()), "name": "Test"}

    with patch("backend.app.tools.linkedin_ads._get_access_token", return_value="test-tok"), \
         patch.dict(os.environ, {"LINKEDIN_ACCOUNT_ID": "999"}), \
         patch("backend.app.tools.linkedin_ads.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[
            _group_response(), _campaign_response(), _creative_response()
        ])
        mock_cls.return_value.__aenter__.return_value = mock_client

        result = await activate_linkedin(
            activation=activation, platform_config={}, creative_url="https://example.com/c.mp4"
        )

    for field in ("campaign_id", "ad_id", "status", "error"):
        assert field in result


@pytest.mark.asyncio
async def test_activate_linkedin_missing_token_returns_failed():
    activation = {"id": str(uuid4()), "name": "Test"}

    with patch("backend.app.tools.linkedin_ads._get_access_token",
               side_effect=RuntimeError("LINKEDIN_ACCESS_TOKEN must be set or access_token must be provided")), \
         patch.dict(os.environ, {"LINKEDIN_ACCOUNT_ID": "999"}):

        result = await activate_linkedin(
            activation=activation, platform_config={}, creative_url="https://example.com/c.mp4"
        )

    assert result["status"] == "failed"
    assert result["campaign_id"] is None
    assert result["ad_id"] is None
    assert result["error"] is not None
    assert "LINKEDIN_ACCESS_TOKEN" in result["error"]


@pytest.mark.asyncio
async def test_activate_linkedin_sends_auth_header():
    activation = {"id": str(uuid4()), "name": "Test Campaign", "cost_estimated": 1000.0}

    with patch("backend.app.tools.linkedin_ads._get_access_token", return_value="my-token"), \
         patch.dict(os.environ, {"LINKEDIN_ACCOUNT_ID": "999"}), \
         patch("backend.app.tools.linkedin_ads.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[
            _group_response(), _campaign_response(), _creative_response()
        ])
        mock_cls.return_value.__aenter__.return_value = mock_client

        await activate_linkedin(
            activation=activation, platform_config={}, creative_url="https://example.com/c.mp4"
        )

        assert mock_client.post.call_count == 3
        for call in mock_client.post.call_args_list:
            assert call.kwargs["headers"]["Authorization"] == "Bearer my-token"


@pytest.mark.asyncio
async def test_activate_linkedin_token_param_overrides_env():
    activation = {"id": str(uuid4()), "name": "Test"}

    with patch.dict(os.environ, {"LINKEDIN_ACCESS_TOKEN": "env-token", "LINKEDIN_ACCOUNT_ID": "999"}), \
         patch("backend.app.tools.linkedin_ads.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[
            _group_response(), _campaign_response(), _creative_response()
        ])
        mock_cls.return_value.__aenter__.return_value = mock_client

        await activate_linkedin(
            activation=activation,
            platform_config={},
            creative_url="https://example.com/c.mp4",
            access_token="explicit-token",
        )

        first_kwargs = mock_client.post.call_args_list[0][1]
        assert first_kwargs["headers"]["Authorization"] == "Bearer explicit-token"
