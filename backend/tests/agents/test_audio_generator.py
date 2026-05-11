"""Tests for Audio Generator Agent (AGT-10)."""

import pytest
from unittest.mock import AsyncMock, patch

from backend.app.agents.audio_generator import (
    VOICE_MAP,
    AudioGenerationBrief,
    AudioGenerationOutput,
    AudioGeneratorAgent,
)


# ---------------------------------------------------------------------------
# Helpers & fixtures
# ---------------------------------------------------------------------------

FAKE_MP3 = b"\xff\xfb\x90\x00" + b"\x00" * 200  # fake MP3 header + padding
FAKE_URL = "https://s3.example.com/camp-001/audio.mp3"
RACHEL_ID = "21m00Tcm4TlvDq8ikWAM"
ANTONI_ID = "ErXwobaYiN019PkySvjV"
DOMI_ID = "AZnzlk1XvdvUeBnXmlld"


class FakeStorageClient:
    def __init__(self, url: str = FAKE_URL):
        self.url = url
        self.calls: list = []

    async def upload(self, data: bytes, key: str) -> str:
        self.calls.append((data, key))
        return self.url


class FakeSession:
    def __init__(self):
        self.rows: list = []

    def add(self, row):
        self.rows.append(row)

    async def commit(self):
        pass


@pytest.fixture
def brief():
    return AudioGenerationBrief(
        campaign_id="camp-001",
        tenant_id="tenant-001",
        script_text="Are you ready to work smarter? Introducing your AI-powered partner.",
        voice_style="warm",
        script_format="radio",
        campaign_theme="Work Smarter",
    )


@pytest.fixture
def storage():
    return FakeStorageClient()


@pytest.fixture
def agent():
    return AudioGeneratorAgent()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestHappyPath:

    async def test_generate_returns_asset_url(self, agent, brief, storage):
        with patch(
            "backend.app.agents.audio_generator.elevenlabs.generate_vo",
            new=AsyncMock(return_value=FAKE_MP3),
        ):
            output = await agent.generate(brief, storage_client=storage)

        assert output.asset_url == FAKE_URL

    async def test_generate_returns_audio_generation_output(self, agent, brief, storage):
        with patch(
            "backend.app.agents.audio_generator.elevenlabs.generate_vo",
            new=AsyncMock(return_value=FAKE_MP3),
        ):
            output = await agent.generate(brief, storage_client=storage)

        assert isinstance(output, AudioGenerationOutput)
        assert output.campaign_id == "camp-001"
        assert output.tenant_id == "tenant-001"

    async def test_storage_client_receives_mp3_bytes(self, agent, brief, storage):
        with patch(
            "backend.app.agents.audio_generator.elevenlabs.generate_vo",
            new=AsyncMock(return_value=FAKE_MP3),
        ):
            await agent.generate(brief, storage_client=storage)

        assert len(storage.calls) == 1
        uploaded_bytes, key = storage.calls[0]
        assert uploaded_bytes == FAKE_MP3
        assert "camp-001" in key

    async def test_no_persist_without_db_session(self, agent, brief, storage):
        with patch(
            "backend.app.agents.audio_generator.elevenlabs.generate_vo",
            new=AsyncMock(return_value=FAKE_MP3),
        ):
            output = await agent.generate(brief, storage_client=storage)

        assert output.asset_url == FAKE_URL  # no error, no DB write


# ---------------------------------------------------------------------------
# Voice selection
# ---------------------------------------------------------------------------

class TestVoiceSelection:

    async def test_warm_style_uses_rachel_voice(self, agent, storage):
        brief = AudioGenerationBrief(
            campaign_id="c", tenant_id="t",
            script_text="Hello world", voice_style="warm",
            script_format="radio",
        )
        with patch(
            "backend.app.agents.audio_generator.elevenlabs.generate_vo",
            new=AsyncMock(return_value=FAKE_MP3),
        ) as mock_vo:
            output = await agent.generate(brief, storage_client=storage)

        assert output.voice_id == RACHEL_ID
        call_kwargs = mock_vo.call_args
        assert RACHEL_ID in call_kwargs[0] or call_kwargs[1].get("voice_id") == RACHEL_ID

    async def test_authoritative_style_uses_antoni_voice(self, agent, storage):
        brief = AudioGenerationBrief(
            campaign_id="c", tenant_id="t",
            script_text="Hello world", voice_style="authoritative",
            script_format="tvc_vo",
        )
        with patch(
            "backend.app.agents.audio_generator.elevenlabs.generate_vo",
            new=AsyncMock(return_value=FAKE_MP3),
        ) as mock_vo:
            output = await agent.generate(brief, storage_client=storage)

        assert output.voice_id == ANTONI_ID

    async def test_youthful_style_uses_domi_voice(self, agent, storage):
        brief = AudioGenerationBrief(
            campaign_id="c", tenant_id="t",
            script_text="Hello world", voice_style="youthful",
            script_format="social_video",
        )
        with patch(
            "backend.app.agents.audio_generator.elevenlabs.generate_vo",
            new=AsyncMock(return_value=FAKE_MP3),
        ) as mock_vo:
            output = await agent.generate(brief, storage_client=storage)

        assert output.voice_id == DOMI_ID

    async def test_invalid_voice_style_raises_value_error(self, agent, storage):
        brief = AudioGenerationBrief(
            campaign_id="c", tenant_id="t",
            script_text="Hello", voice_style="mysterious",
            script_format="radio",
        )
        with pytest.raises(ValueError, match="Unknown voice_style"):
            await agent.generate(brief, storage_client=storage)

    async def test_invalid_voice_style_makes_no_api_call(self, agent, storage):
        brief = AudioGenerationBrief(
            campaign_id="c", tenant_id="t",
            script_text="Hello", voice_style="unknown",
            script_format="radio",
        )
        mock_vo = AsyncMock(return_value=FAKE_MP3)
        with patch("backend.app.agents.audio_generator.elevenlabs.generate_vo", new=mock_vo):
            with pytest.raises(ValueError):
                await agent.generate(brief, storage_client=storage)

        mock_vo.assert_not_called()


# ---------------------------------------------------------------------------
# Duration estimation
# ---------------------------------------------------------------------------

class TestDuration:

    async def test_duration_seconds_estimated_from_char_count(self, agent, storage):
        script = "x" * 300  # 300 chars → 2.0 seconds
        brief = AudioGenerationBrief(
            campaign_id="c", tenant_id="t",
            script_text=script, voice_style="warm",
            script_format="radio",
        )
        with patch(
            "backend.app.agents.audio_generator.elevenlabs.generate_vo",
            new=AsyncMock(return_value=FAKE_MP3),
        ):
            output = await agent.generate(brief, storage_client=storage)

        assert output.duration_seconds == pytest.approx(2.0)

    async def test_duration_seconds_is_positive(self, agent, brief, storage):
        with patch(
            "backend.app.agents.audio_generator.elevenlabs.generate_vo",
            new=AsyncMock(return_value=FAKE_MP3),
        ):
            output = await agent.generate(brief, storage_client=storage)

        assert output.duration_seconds > 0


# ---------------------------------------------------------------------------
# Retry behavior
# ---------------------------------------------------------------------------

class TestRetryBehavior:

    async def test_retry_exhausted_raises(self, agent, brief, storage):
        call_count = 0

        async def always_fail(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise RuntimeError("ElevenLabs down")

        with patch(
            "backend.app.agents.audio_generator.elevenlabs.generate_vo",
            new=always_fail,
        ):
            with pytest.raises(RuntimeError, match="ElevenLabs down"):
                await agent.generate(brief, storage_client=storage)

        assert call_count == 3

    async def test_retry_succeeds_on_third_attempt(self, agent, brief, storage):
        call_count = 0

        async def flaky(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("transient")
            return FAKE_MP3

        with patch(
            "backend.app.agents.audio_generator.elevenlabs.generate_vo",
            new=flaky,
        ):
            output = await agent.generate(brief, storage_client=storage)

        assert call_count == 3
        assert output.asset_url == FAKE_URL


# ---------------------------------------------------------------------------
# DB persistence
# ---------------------------------------------------------------------------

class TestPersistence:

    async def test_persist_creates_db_record_with_tenant_id(self, agent, brief, storage):
        session = FakeSession()
        with patch(
            "backend.app.agents.audio_generator.elevenlabs.generate_vo",
            new=AsyncMock(return_value=FAKE_MP3),
        ):
            await agent.generate(brief, storage_client=storage, db_session=session)

        assert len(session.rows) == 1
        row = session.rows[0]
        assert row.tenant_id == "tenant-001"
        assert row.campaign_id == "camp-001"

    async def test_persist_stores_voice_id(self, agent, brief, storage):
        session = FakeSession()
        with patch(
            "backend.app.agents.audio_generator.elevenlabs.generate_vo",
            new=AsyncMock(return_value=FAKE_MP3),
        ):
            await agent.generate(brief, storage_client=storage, db_session=session)

        assert session.rows[0].voice_id == RACHEL_ID
