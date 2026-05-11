"""Tests for Image Generator Agent (AGT-09)."""

import base64
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.agents.image_generator import (
    IMAGE_DIMENSIONS,
    ImageGenerationBrief,
    ImageGenerationOutput,
    ImageGeneratorAgent,
)


# ---------------------------------------------------------------------------
# Helpers & fixtures
# ---------------------------------------------------------------------------

FAKE_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
FAKE_URL = "https://s3.example.com/camp-001/test-image.png"
ENRICHED_PROMPT = "Modern minimalist office, golden hour lighting, 8K, photorealistic, Canon EOS, wide angle"


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


def _make_anthropic_client(text: str = ENRICHED_PROMPT, raises: bool = False):
    client = MagicMock()
    if raises:
        client.messages.create = AsyncMock(side_effect=RuntimeError("Haiku down"))
    else:
        resp = MagicMock()
        resp.content = [MagicMock(text=text)]
        client.messages.create = AsyncMock(return_value=resp)
    return client


def _make_dalle_client(image_bytes: bytes = FAKE_PNG, raises: bool = False):
    client = MagicMock()
    if raises:
        client.images.generate = AsyncMock(side_effect=RuntimeError("DALL-E down"))
    else:
        resp = MagicMock()
        resp.data = [MagicMock(b64_json=base64.b64encode(image_bytes).decode())]
        client.images.generate = AsyncMock(return_value=resp)
    return client


@pytest.fixture
def brief():
    return ImageGenerationBrief(
        campaign_id="camp-001",
        tenant_id="tenant-001",
        image_format="square",
        visual_direction="Modern minimalist office with natural light",
        brand_palette=["#FFFFFF", "#0066CC", "#333333"],
        tone_adjectives=["bold", "clean", "professional"],
        campaign_theme="Work Smarter",
        style_notes="Shot on Canon EOS",
    )


@pytest.fixture
def storage():
    return FakeStorageClient()


@pytest.fixture
def agent():
    a = ImageGeneratorAgent()
    a.anthropic_client = _make_anthropic_client()
    return a


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestHappyPath:

    async def test_generate_returns_asset_url(self, agent, brief, storage):
        with patch(
            "backend.app.agents.image_generator.stability_ai.generate_image",
            new=AsyncMock(return_value=FAKE_PNG),
        ):
            output = await agent.generate(brief, storage_client=storage)

        assert output.asset_url == FAKE_URL

    async def test_generate_returns_image_generation_output(self, agent, brief, storage):
        with patch(
            "backend.app.agents.image_generator.stability_ai.generate_image",
            new=AsyncMock(return_value=FAKE_PNG),
        ):
            output = await agent.generate(brief, storage_client=storage)

        assert isinstance(output, ImageGenerationOutput)
        assert output.campaign_id == "camp-001"
        assert output.tenant_id == "tenant-001"

    async def test_model_used_stability_on_success(self, agent, brief, storage):
        with patch(
            "backend.app.agents.image_generator.stability_ai.generate_image",
            new=AsyncMock(return_value=FAKE_PNG),
        ):
            output = await agent.generate(brief, storage_client=storage)

        assert output.model_used == "stability-sdxl"

    async def test_storage_client_receives_bytes(self, agent, brief, storage):
        with patch(
            "backend.app.agents.image_generator.stability_ai.generate_image",
            new=AsyncMock(return_value=FAKE_PNG),
        ):
            await agent.generate(brief, storage_client=storage)

        assert len(storage.calls) == 1
        uploaded_bytes, key = storage.calls[0]
        assert uploaded_bytes == FAKE_PNG
        assert "camp-001" in key


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

class TestPromptBuilder:

    async def test_prompt_contains_visual_direction(self, agent, brief, storage):
        with patch(
            "backend.app.agents.image_generator.stability_ai.generate_image",
            new=AsyncMock(return_value=FAKE_PNG),
        ):
            output = await agent.generate(brief, storage_client=storage)

        assert brief.visual_direction in output.prompt_used or ENRICHED_PROMPT in output.prompt_used

    async def test_prompt_enrichment_fails_gracefully(self, brief, storage):
        agent = ImageGeneratorAgent()
        agent.anthropic_client = _make_anthropic_client(raises=True)

        with patch(
            "backend.app.agents.image_generator.stability_ai.generate_image",
            new=AsyncMock(return_value=FAKE_PNG),
        ):
            output = await agent.generate(brief, storage_client=storage)

        # Must still succeed using base template
        assert output.asset_url == FAKE_URL
        assert brief.visual_direction in output.prompt_used


# ---------------------------------------------------------------------------
# Dimensions
# ---------------------------------------------------------------------------

class TestDimensions:

    async def test_square_format_dimensions(self, agent, storage):
        brief = ImageGenerationBrief(
            campaign_id="c", tenant_id="t", image_format="square",
            visual_direction="test", brand_palette=[], tone_adjectives=[],
            campaign_theme="T",
        )
        with patch(
            "backend.app.agents.image_generator.stability_ai.generate_image",
            new=AsyncMock(return_value=FAKE_PNG),
        ) as mock_gen:
            await agent.generate(brief, storage_client=storage)

        _, kwargs = mock_gen.call_args
        assert kwargs.get("width", mock_gen.call_args[0][1] if len(mock_gen.call_args[0]) > 1 else None) == 1024 or \
               mock_gen.call_args[0][1] == 1024

    async def test_square_params_in_output(self, agent, storage):
        brief = ImageGenerationBrief(
            campaign_id="c", tenant_id="t", image_format="square",
            visual_direction="test", brand_palette=[], tone_adjectives=[],
            campaign_theme="T",
        )
        with patch(
            "backend.app.agents.image_generator.stability_ai.generate_image",
            new=AsyncMock(return_value=FAKE_PNG),
        ):
            output = await agent.generate(brief, storage_client=storage)

        assert output.generation_params["width"] == 1024
        assert output.generation_params["height"] == 1024

    async def test_landscape_params_in_output(self, agent, storage):
        brief = ImageGenerationBrief(
            campaign_id="c", tenant_id="t", image_format="landscape",
            visual_direction="test", brand_palette=[], tone_adjectives=[],
            campaign_theme="T",
        )
        with patch(
            "backend.app.agents.image_generator.stability_ai.generate_image",
            new=AsyncMock(return_value=FAKE_PNG),
        ):
            output = await agent.generate(brief, storage_client=storage)

        assert output.generation_params["width"] == 1344
        assert output.generation_params["height"] == 768

    async def test_portrait_params_in_output(self, agent, storage):
        brief = ImageGenerationBrief(
            campaign_id="c", tenant_id="t", image_format="portrait",
            visual_direction="test", brand_palette=[], tone_adjectives=[],
            campaign_theme="T",
        )
        with patch(
            "backend.app.agents.image_generator.stability_ai.generate_image",
            new=AsyncMock(return_value=FAKE_PNG),
        ):
            output = await agent.generate(brief, storage_client=storage)

        assert output.generation_params["width"] == 768
        assert output.generation_params["height"] == 1344

    async def test_invalid_format_raises_value_error(self, agent, storage):
        brief = ImageGenerationBrief(
            campaign_id="c", tenant_id="t", image_format="square",
            visual_direction="test", brand_palette=[], tone_adjectives=[],
            campaign_theme="T",
        )
        bad_brief = brief.model_copy(update={"image_format": "panoramic"})

        with pytest.raises(ValueError, match="Unknown image_format"):
            await agent.generate(bad_brief, storage_client=storage)


# ---------------------------------------------------------------------------
# Fallback / error handling
# ---------------------------------------------------------------------------

class TestFallback:

    async def test_fallback_to_dalle_on_stability_failure(self, brief, storage):
        dalle_client = _make_dalle_client()
        agent = ImageGeneratorAgent(openai_client=dalle_client)
        agent.anthropic_client = _make_anthropic_client()

        with patch(
            "backend.app.agents.image_generator.stability_ai.generate_image",
            new=AsyncMock(side_effect=RuntimeError("Stability down")),
        ):
            output = await agent.generate(brief, storage_client=storage)

        assert output.asset_url == FAKE_URL
        dalle_client.images.generate.assert_called_once()

    async def test_model_used_dalle_on_fallback(self, brief, storage):
        dalle_client = _make_dalle_client()
        agent = ImageGeneratorAgent(openai_client=dalle_client)
        agent.anthropic_client = _make_anthropic_client()

        with patch(
            "backend.app.agents.image_generator.stability_ai.generate_image",
            new=AsyncMock(side_effect=RuntimeError("Stability down")),
        ):
            output = await agent.generate(brief, storage_client=storage)

        assert output.model_used == "dall-e-3"

    async def test_both_providers_fail_raises(self, brief, storage):
        dalle_client = _make_dalle_client(raises=True)
        agent = ImageGeneratorAgent(openai_client=dalle_client)
        agent.anthropic_client = _make_anthropic_client()

        with patch(
            "backend.app.agents.image_generator.stability_ai.generate_image",
            new=AsyncMock(side_effect=RuntimeError("Stability down")),
        ):
            with pytest.raises(RuntimeError, match="All image generation providers failed"):
                await agent.generate(brief, storage_client=storage)

    async def test_stability_retried_before_fallback(self, brief, storage):
        call_count = 0

        async def flaky_stability(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise RuntimeError("transient")

        dalle_client = _make_dalle_client()
        agent = ImageGeneratorAgent(openai_client=dalle_client)
        agent.anthropic_client = _make_anthropic_client()

        with patch(
            "backend.app.agents.image_generator.stability_ai.generate_image",
            new=flaky_stability,
        ):
            await agent.generate(brief, storage_client=storage)

        assert call_count == 2  # MAX_RETRIES=2


# ---------------------------------------------------------------------------
# DB persistence
# ---------------------------------------------------------------------------

class TestPersistence:

    async def test_persist_creates_db_record_with_tenant_id(self, agent, brief, storage):
        session = FakeSession()
        with patch(
            "backend.app.agents.image_generator.stability_ai.generate_image",
            new=AsyncMock(return_value=FAKE_PNG),
        ):
            await agent.generate(brief, storage_client=storage, db_session=session)

        assert len(session.rows) == 1
        assert session.rows[0].tenant_id == "tenant-001"
        assert session.rows[0].campaign_id == "camp-001"

    async def test_no_persist_without_db_session(self, agent, brief, storage):
        with patch(
            "backend.app.agents.image_generator.stability_ai.generate_image",
            new=AsyncMock(return_value=FAKE_PNG),
        ):
            output = await agent.generate(brief, storage_client=storage)

        assert output.asset_url == FAKE_URL  # no error, just no DB write
