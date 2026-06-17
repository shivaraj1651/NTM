"""Tests for the Runway ML video generation tool."""
import os
from unittest.mock import AsyncMock, patch

import pytest

from backend.app.tools.runway import generate_video, get_video_status, is_available


def _post_response(job_id: str = "rw-job-001"):
    m = AsyncMock()
    m.status_code = 200
    m.json = lambda: {"id": job_id}
    return m


def _status_response(status: str = "SUCCEEDED", url: str | None = "https://cdn.runwayml.com/v.mp4"):
    m = AsyncMock()
    m.status_code = 200
    output = [url] if url else []
    m.json = lambda: {"status": status, "output": output}
    return m


def test_is_available_false_when_no_key():
    with patch.dict(os.environ, {"RUNWAY_API_KEY": ""}, clear=False):
        assert is_available() is False


def test_is_available_true_when_key_set():
    with patch.dict(os.environ, {"RUNWAY_API_KEY": "rw-secret"}):
        assert is_available() is True


@pytest.mark.asyncio
async def test_generate_video_no_api_key_raises():
    with patch.dict(os.environ, {"RUNWAY_API_KEY": ""}, clear=False):
        with pytest.raises(RuntimeError, match="RUNWAY_API_KEY not set"):
            await generate_video("a cinematic scene", image_url=None)


@pytest.mark.asyncio
async def test_generate_video_text_only_uses_text_endpoint():
    with patch.dict(os.environ, {"RUNWAY_API_KEY": "rw-key"}), \
         patch("backend.app.tools.runway.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_post_response())
        mock_cls.return_value.__aenter__.return_value = mock_client

        job_id = await generate_video("cinematic sunrise", image_url=None, duration=5)

    assert job_id == "rw-job-001"
    url = mock_client.post.call_args[0][0]
    assert "text_to_video" in url


@pytest.mark.asyncio
async def test_generate_video_with_image_uses_image_endpoint():
    with patch.dict(os.environ, {"RUNWAY_API_KEY": "rw-key"}), \
         patch("backend.app.tools.runway.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_post_response("rw-job-img-001"))
        mock_cls.return_value.__aenter__.return_value = mock_client

        job_id = await generate_video("cinematic sunrise", image_url="https://example.com/img.jpg", duration=10)

    assert job_id == "rw-job-img-001"
    url = mock_client.post.call_args[0][0]
    assert "image_to_video" in url
    payload = mock_client.post.call_args[1]["json"]
    assert payload["promptImage"] == "https://example.com/img.jpg"


@pytest.mark.asyncio
async def test_generate_video_api_error_raises():
    with patch.dict(os.environ, {"RUNWAY_API_KEY": "rw-key"}), \
         patch("backend.app.tools.runway.httpx.AsyncClient") as mock_cls:

        error_resp = AsyncMock()
        error_resp.status_code = 500
        error_resp.text = "Internal error"
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=error_resp)
        mock_cls.return_value.__aenter__.return_value = mock_client

        with pytest.raises(RuntimeError, match="Runway returned 500"):
            await generate_video("test", image_url=None)


@pytest.mark.asyncio
async def test_generate_video_missing_id_raises():
    with patch.dict(os.environ, {"RUNWAY_API_KEY": "rw-key"}), \
         patch("backend.app.tools.runway.httpx.AsyncClient") as mock_cls:

        no_id_resp = AsyncMock()
        no_id_resp.status_code = 200
        no_id_resp.json = lambda: {"status": "PENDING"}
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=no_id_resp)
        mock_cls.return_value.__aenter__.return_value = mock_client

        with pytest.raises(RuntimeError, match="missing 'id' field"):
            await generate_video("test", image_url=None)


@pytest.mark.asyncio
async def test_generate_video_sends_version_header():
    with patch.dict(os.environ, {"RUNWAY_API_KEY": "rw-key"}), \
         patch("backend.app.tools.runway.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_post_response())
        mock_cls.return_value.__aenter__.return_value = mock_client

        await generate_video("test", image_url=None)

        headers = mock_client.post.call_args[1]["headers"]
        assert "X-Runway-Version" in headers
        assert headers["Authorization"] == "Bearer rw-key"


@pytest.mark.asyncio
async def test_get_video_status_succeeded():
    with patch.dict(os.environ, {"RUNWAY_API_KEY": "rw-key"}), \
         patch("backend.app.tools.runway.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_status_response("SUCCEEDED", "https://cdn.runwayml.com/v.mp4"))
        mock_cls.return_value.__aenter__.return_value = mock_client

        result = await get_video_status("rw-job-001")

    assert result["status"] == "SUCCEEDED"
    assert result["url"] == "https://cdn.runwayml.com/v.mp4"


@pytest.mark.asyncio
async def test_get_video_status_pending():
    with patch.dict(os.environ, {"RUNWAY_API_KEY": "rw-key"}), \
         patch("backend.app.tools.runway.httpx.AsyncClient") as mock_cls:

        pending = AsyncMock()
        pending.status_code = 200
        pending.json = lambda: {"status": "PENDING", "output": []}
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=pending)
        mock_cls.return_value.__aenter__.return_value = mock_client

        result = await get_video_status("rw-job-001")

    assert result["status"] == "PENDING"
    assert result["url"] is None


@pytest.mark.asyncio
async def test_get_video_status_no_api_key_raises():
    with patch.dict(os.environ, {"RUNWAY_API_KEY": ""}, clear=False):
        with pytest.raises(RuntimeError, match="RUNWAY_API_KEY not set"):
            await get_video_status("rw-job-001")


@pytest.mark.asyncio
async def test_get_video_status_api_error_raises():
    with patch.dict(os.environ, {"RUNWAY_API_KEY": "rw-key"}), \
         patch("backend.app.tools.runway.httpx.AsyncClient") as mock_cls:

        error_resp = AsyncMock()
        error_resp.status_code = 404
        error_resp.text = "Not Found"
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=error_resp)
        mock_cls.return_value.__aenter__.return_value = mock_client

        with pytest.raises(RuntimeError, match="Runway status check returned 404"):
            await get_video_status("bad-job-id")
