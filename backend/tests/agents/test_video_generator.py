"""Tests for Video Generator Agent (AGT-11)."""

import pytest
from unittest.mock import AsyncMock, patch

from backend.app.agents.video_generator import (
    RUNWAY_MODEL,
    STATUS_COMPLETED,
    STATUS_MANUAL,
    VideoGenerationBrief,
    VideoGenerationOutput,
    VideoGeneratorAgent,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FAKE_MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 200
FAKE_URL = "https://s3.example.com/camp-001/video.mp4"
FAKE_JOB_ID = "runway-job-001"
FAKE_RUNWAY_URL = "https://runway-cdn.example.com/output.mp4"

SUCCEEDED_STATUS = {"status": "SUCCEEDED", "url": FAKE_RUNWAY_URL}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeHTTPResponse:
    def __init__(self, content=FAKE_MP4):
        self.content = content


class FakeHTTPClient:
    """Replaces httpx.AsyncClient for the MP4 download step."""
    def __init__(self, content=FAKE_MP4, **kwargs):
        self._content = content

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def get(self, url):
        return FakeHTTPResponse(self._content)


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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def brief():
    return VideoGenerationBrief(
        campaign_id="camp-001",
        tenant_id="tenant-001",
        prompt="A product flying through space with neon trails",
        script_text="Introducing the future. Available now.",
        reference_image_url="https://s3.example.com/camp-001/image.png",
        duration_seconds=5,
        campaign_theme="Future Tech",
    )


@pytest.fixture
def storage():
    return FakeStorageClient()


@pytest.fixture
def agent():
    return VideoGeneratorAgent()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestHappyPath:

    async def test_generate_returns_asset_url(self, agent, brief, storage):
        with patch(
            "backend.app.agents.video_generator.runway.generate_video",
            new=AsyncMock(return_value=FAKE_JOB_ID),
        ), patch(
            "backend.app.agents.video_generator.runway.get_video_status",
            new=AsyncMock(return_value=SUCCEEDED_STATUS),
        ), patch(
            "backend.app.agents.video_generator.httpx.AsyncClient",
            FakeHTTPClient,
        ):
            output = await agent.generate(brief, storage_client=storage)

        assert output.asset_url == FAKE_URL

    async def test_generate_returns_video_generation_output(self, agent, brief, storage):
        with patch(
            "backend.app.agents.video_generator.runway.generate_video",
            new=AsyncMock(return_value=FAKE_JOB_ID),
        ), patch(
            "backend.app.agents.video_generator.runway.get_video_status",
            new=AsyncMock(return_value=SUCCEEDED_STATUS),
        ), patch(
            "backend.app.agents.video_generator.httpx.AsyncClient",
            FakeHTTPClient,
        ):
            output = await agent.generate(brief, storage_client=storage)

        assert isinstance(output, VideoGenerationOutput)
        assert output.campaign_id == "camp-001"
        assert output.tenant_id == "tenant-001"
        assert output.status == STATUS_COMPLETED
        assert output.job_id == FAKE_JOB_ID

    async def test_storage_client_receives_mp4_bytes(self, agent, brief, storage):
        with patch(
            "backend.app.agents.video_generator.runway.generate_video",
            new=AsyncMock(return_value=FAKE_JOB_ID),
        ), patch(
            "backend.app.agents.video_generator.runway.get_video_status",
            new=AsyncMock(return_value=SUCCEEDED_STATUS),
        ), patch(
            "backend.app.agents.video_generator.httpx.AsyncClient",
            FakeHTTPClient,
        ):
            await agent.generate(brief, storage_client=storage)

        assert len(storage.calls) == 1
        uploaded_bytes, key = storage.calls[0]
        assert uploaded_bytes == FAKE_MP4
        assert "camp-001" in key
        assert key.endswith(".mp4")

    async def test_no_persist_without_db_session(self, agent, brief, storage):
        with patch(
            "backend.app.agents.video_generator.runway.generate_video",
            new=AsyncMock(return_value=FAKE_JOB_ID),
        ), patch(
            "backend.app.agents.video_generator.runway.get_video_status",
            new=AsyncMock(return_value=SUCCEEDED_STATUS),
        ), patch(
            "backend.app.agents.video_generator.httpx.AsyncClient",
            FakeHTTPClient,
        ):
            output = await agent.generate(brief, storage_client=storage)

        assert output.asset_url == FAKE_URL  # no error, no DB write


# ---------------------------------------------------------------------------
# Image-to-video routing
# ---------------------------------------------------------------------------

class TestImageToVideo:

    async def test_image_url_passed_to_runway_tool(self, agent, storage):
        brief = VideoGenerationBrief(
            campaign_id="c", tenant_id="t",
            prompt="product in space",
            script_text="Introducing.",
            reference_image_url="https://s3.example.com/image.png",
            duration_seconds=5,
        )
        mock_generate = AsyncMock(return_value=FAKE_JOB_ID)
        with patch(
            "backend.app.agents.video_generator.runway.generate_video",
            new=mock_generate,
        ), patch(
            "backend.app.agents.video_generator.runway.get_video_status",
            new=AsyncMock(return_value=SUCCEEDED_STATUS),
        ), patch(
            "backend.app.agents.video_generator.httpx.AsyncClient",
            FakeHTTPClient,
        ):
            await agent.generate(brief, storage_client=storage)

        call_args = mock_generate.call_args
        assert call_args[0][1] == "https://s3.example.com/image.png"

    async def test_no_image_url_uses_text_to_video(self, agent, storage):
        brief = VideoGenerationBrief(
            campaign_id="c", tenant_id="t",
            prompt="product in space",
            script_text="Introducing.",
            reference_image_url=None,
            duration_seconds=5,
        )
        mock_generate = AsyncMock(return_value=FAKE_JOB_ID)
        with patch(
            "backend.app.agents.video_generator.runway.generate_video",
            new=mock_generate,
        ), patch(
            "backend.app.agents.video_generator.runway.get_video_status",
            new=AsyncMock(return_value=SUCCEEDED_STATUS),
        ), patch(
            "backend.app.agents.video_generator.httpx.AsyncClient",
            FakeHTTPClient,
        ):
            await agent.generate(brief, storage_client=storage)

        call_args = mock_generate.call_args
        assert call_args[0][1] is None
