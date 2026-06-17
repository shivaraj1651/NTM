"""Tests for the ElevenLabs TTS tool."""
import os
from unittest.mock import AsyncMock, patch

import pytest

from backend.app.tools.elevenlabs import _SILENT_MP3_PLACEHOLDER, generate_vo, is_available


def test_is_available_false_when_no_key():
    with patch.dict(os.environ, {"ELEVENLABS_API_KEY": ""}, clear=False):
        assert is_available() is False


def test_is_available_true_when_key_set():
    with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "el-test-key"}):
        assert is_available() is True


@pytest.mark.asyncio
async def test_generate_vo_returns_placeholder_when_no_key():
    with patch.dict(os.environ, {"ELEVENLABS_API_KEY": ""}, clear=False):
        result = await generate_vo("Hello world", voice_id="21m00Tcm4TlvDq8ikWAM")
    assert result == _SILENT_MP3_PLACEHOLDER
    assert isinstance(result, bytes)


@pytest.mark.asyncio
async def test_generate_vo_success():
    fake_audio = b"\xff\xfb\x90\x00" + b"\x00" * 100

    with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "el-test-key"}), \
         patch("backend.app.tools.elevenlabs.httpx.AsyncClient") as mock_cls:

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.content = fake_audio
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_cls.return_value.__aenter__.return_value = mock_client

        result = await generate_vo("Hello world", voice_id="21m00Tcm4TlvDq8ikWAM")

    assert result == fake_audio


@pytest.mark.asyncio
async def test_generate_vo_sends_correct_headers_and_payload():
    with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "el-key-123"}), \
         patch("backend.app.tools.elevenlabs.httpx.AsyncClient") as mock_cls:

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.content = b"audio_bytes"
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_cls.return_value.__aenter__.return_value = mock_client

        await generate_vo("Test script", voice_id="voice123", model="eleven_multilingual_v2")

        call_kwargs = mock_client.post.call_args[1]
        assert call_kwargs["headers"]["xi-api-key"] == "el-key-123"
        assert call_kwargs["headers"]["Accept"] == "audio/mpeg"
        assert call_kwargs["json"]["text"] == "Test script"
        assert call_kwargs["json"]["model_id"] == "eleven_multilingual_v2"


@pytest.mark.asyncio
async def test_generate_vo_api_error_raises():
    with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "el-test-key"}), \
         patch("backend.app.tools.elevenlabs.httpx.AsyncClient") as mock_cls:

        mock_response = AsyncMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_cls.return_value.__aenter__.return_value = mock_client

        with pytest.raises(RuntimeError, match="ElevenLabs returned 401"):
            await generate_vo("script", voice_id="voice123")


@pytest.mark.asyncio
async def test_generate_vo_url_includes_voice_id():
    with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "el-key"}), \
         patch("backend.app.tools.elevenlabs.httpx.AsyncClient") as mock_cls:

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.content = b"audio"
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_cls.return_value.__aenter__.return_value = mock_client

        await generate_vo("text", voice_id="my-voice-id")

        url = mock_client.post.call_args[0][0]
        assert "my-voice-id" in url
