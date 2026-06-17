"""Tests for the Stability AI SDXL image generation tool."""
import base64
import os
from unittest.mock import AsyncMock, patch

import pytest

from backend.app.tools.stability_ai import generate_image

_FAKE_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
_FAKE_B64 = base64.b64encode(_FAKE_PNG).decode()


def _ok_response(b64: str = _FAKE_B64):
    m = AsyncMock()
    m.status_code = 200
    m.json = lambda: {"artifacts": [{"base64": b64, "finishReason": "SUCCESS"}]}
    return m


def _error_response(status: int = 500, text: str = "Internal Server Error"):
    m = AsyncMock()
    m.status_code = status
    m.text = text
    m.json = lambda: {}
    return m


@pytest.mark.asyncio
async def test_generate_image_missing_api_key():
    with patch.dict(os.environ, {"STABILITY_AI_API_KEY": ""}, clear=False):
        with pytest.raises(RuntimeError, match="STABILITY_AI_API_KEY not set"):
            await generate_image("a sunset over the ocean")


@pytest.mark.asyncio
async def test_generate_image_success():
    with patch.dict(os.environ, {"STABILITY_AI_API_KEY": "sk-test"}), \
         patch("backend.app.tools.stability_ai.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_ok_response())
        mock_cls.return_value.__aenter__.return_value = mock_client

        result = await generate_image("a sunset over the ocean", width=1344, height=768)

    assert isinstance(result, bytes)
    assert result == _FAKE_PNG


@pytest.mark.asyncio
async def test_generate_image_passes_dimensions():
    with patch.dict(os.environ, {"STABILITY_AI_API_KEY": "sk-test"}), \
         patch("backend.app.tools.stability_ai.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_ok_response())
        mock_cls.return_value.__aenter__.return_value = mock_client

        await generate_image("test prompt", width=768, height=1344, steps=20, cfg_scale=8.0)

        payload = mock_client.post.call_args[1]["json"]
        assert payload["width"] == 768
        assert payload["height"] == 1344
        assert payload["steps"] == 20
        assert payload["cfg_scale"] == 8.0
        assert payload["text_prompts"][0]["text"] == "test prompt"


@pytest.mark.asyncio
async def test_generate_image_api_error_raises():
    with patch.dict(os.environ, {"STABILITY_AI_API_KEY": "sk-test"}), \
         patch("backend.app.tools.stability_ai.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_error_response(500, "server error"))
        mock_cls.return_value.__aenter__.return_value = mock_client

        with pytest.raises(RuntimeError, match="Stability AI returned 500"):
            await generate_image("test")


@pytest.mark.asyncio
async def test_generate_image_no_artifacts_raises():
    with patch.dict(os.environ, {"STABILITY_AI_API_KEY": "sk-test"}), \
         patch("backend.app.tools.stability_ai.httpx.AsyncClient") as mock_cls:

        empty = AsyncMock()
        empty.status_code = 200
        empty.json = lambda: {"artifacts": []}
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=empty)
        mock_cls.return_value.__aenter__.return_value = mock_client

        with pytest.raises(RuntimeError, match="no artifacts"):
            await generate_image("test")


@pytest.mark.asyncio
async def test_generate_image_sends_auth_header():
    with patch.dict(os.environ, {"STABILITY_AI_API_KEY": "sk-secret"}), \
         patch("backend.app.tools.stability_ai.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_ok_response())
        mock_cls.return_value.__aenter__.return_value = mock_client

        await generate_image("test")

        headers = mock_client.post.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer sk-secret"
        assert headers["Content-Type"] == "application/json"
