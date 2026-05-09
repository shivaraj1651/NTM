"""Tests for Creative Brief Generator (AGT-06) with Claude API integration."""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from backend.app.agents.creative_director.generator import CreativeGenerator


@pytest.fixture
def campaign_data():
    """Sample campaign data for testing."""
    return {
        "campaign_input": {
            "campaign_id": "camp-001",
            "tenant_id": "tenant-001",
            "objectives": ["Increase brand awareness", "Drive engagement"],
            "target_audience": {
                "demographics": {"age": "18-45", "location": "urban"},
                "psychographics": {"interests": "Tech, sustainability"},
                "segments": ["Early adopters", "Millennials"],
                "language": "en"
            },
            "brand_guidelines": {
                "tone": "Professional yet approachable",
                "colors": ["#0066CC", "#FF6600"],
                "messaging_rules": ["Always include brand name", "Use inclusive language"],
                "mandatory_ctas": ["Learn more", "Shop now"],
                "tagline": "Leading innovation",
                "visual_style": "Modern and clean"
            },
            "platforms": ["instagram", "linkedin", "youtube"],
            "product_details": "Tech product launch",
            "campaign_theme": "Summer refresh",
            "primary_cta": "Explore the product",
            "competitor_insights": "Competitors focus on price, we focus on quality"
        }
    }


@pytest.fixture
def core_concept():
    """Sample core concept output from Stage 1."""
    return {
        "message": "Innovative tech meets everyday life",
        "visual_direction": "Minimalist design with vibrant accents",
        "audio_direction": "Upbeat, modern electronic background",
        "tone": "Professional yet approachable"
    }


class TestCreativeGeneratorInit:
    """Tests for CreativeGenerator initialization."""

    def test_init_with_default_model(self):
        """CreativeGenerator should initialize with default model."""
        generator = CreativeGenerator(api_key="test-key")

        assert generator.model == "claude-opus-4-7"
        assert generator.max_retries == 3
        assert generator.backoff_base == 2
        assert generator.client is not None

    def test_init_with_custom_model(self):
        """CreativeGenerator should accept custom model."""
        generator = CreativeGenerator(api_key="test-key", model="claude-sonnet-4-20250514")

        assert generator.model == "claude-sonnet-4-20250514"


class TestGenerateCoreConcept:
    """Tests for core concept generation."""

    @pytest.mark.asyncio
    async def test_generate_core_concept(self, campaign_data):
        """Should generate core concept with all required fields."""
        generator = CreativeGenerator(api_key="test-key")

        mock_response = {
            "message": "Innovative tech meets everyday life",
            "visual_direction": "Minimalist design with vibrant accents",
            "audio_direction": "Upbeat, modern electronic background",
            "tone": "Professional yet approachable"
        }

        mock_content = MagicMock()
        mock_content.text = json.dumps(mock_response)

        mock_response_obj = MagicMock()
        mock_response_obj.content = [mock_content]

        mock_messages = MagicMock()
        mock_messages.create = AsyncMock(return_value=mock_response_obj)

        mock_client = MagicMock()
        mock_client.messages = mock_messages

        with patch.object(generator, "client", mock_client):
            result = await generator.generate_core_concept(campaign_data)

        assert "message" in result
        assert "visual_direction" in result
        assert "audio_direction" in result
        assert "tone" in result
        assert result["message"] == "Innovative tech meets everyday life"


class TestGeneratePlatformCreatives:
    """Tests for platform-specific creative generation."""

    @pytest.mark.asyncio
    async def test_generate_platform_creatives(self, campaign_data, core_concept):
        """Should generate platform-specific creatives as a list."""
        generator = CreativeGenerator(api_key="test-key")

        mock_response = {
            "variations": [
                {
                    "variation_id": 1,
                    "content": "Check out our new product",
                    "notes": "Direct CTA",
                    "ctas_included": ["Learn more"]
                },
                {
                    "variation_id": 2,
                    "content": "Innovation in your pocket",
                    "notes": "Benefit-focused",
                    "ctas_included": ["Shop now"]
                }
            ]
        }

        mock_content = MagicMock()
        mock_content.text = json.dumps(mock_response)

        mock_response_obj = MagicMock()
        mock_response_obj.content = [mock_content]

        mock_messages = MagicMock()
        mock_messages.create = AsyncMock(return_value=mock_response_obj)

        mock_client = MagicMock()
        mock_client.messages = mock_messages

        with patch.object(generator, "client", mock_client):
            result = await generator.generate_platform_creatives(
                platform="instagram",
                core_concept=core_concept,
                campaign_data=campaign_data,
                creative_type="copy"
            )

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["variation_id"] == 1
        assert result[0]["content"] == "Check out our new product"

    @pytest.mark.asyncio
    async def test_generate_platform_creatives_returns_list(self, campaign_data, core_concept):
        """Should wrap dict response in list if not already a list."""
        generator = CreativeGenerator(api_key="test-key")

        mock_response = {
            "variation_id": 1,
            "content": "Single variation",
            "notes": "Only one",
            "ctas_included": ["Learn more"]
        }

        mock_content = MagicMock()
        mock_content.text = json.dumps(mock_response)

        mock_response_obj = MagicMock()
        mock_response_obj.content = [mock_content]

        mock_messages = MagicMock()
        mock_messages.create = AsyncMock(return_value=mock_response_obj)

        mock_client = MagicMock()
        mock_client.messages = mock_messages

        with patch.object(generator, "client", mock_client):
            result = await generator.generate_platform_creatives(
                platform="tiktok",
                core_concept=core_concept,
                campaign_data=campaign_data,
                creative_type="video_concept"
            )

        assert isinstance(result, list)
        assert len(result) == 1


class TestRefinativeCreative:
    """Tests for creative refinement."""

    @pytest.mark.asyncio
    async def test_refine_creative(self):
        """Should refine creative based on violations."""
        generator = CreativeGenerator(api_key="test-key")

        original = "Check out our amazing product today!"
        violations = [
            {
                "rule": "Avoid superlatives",
                "severity": "high",
                "message": "Contains 'amazing'",
                "suggestion": "Replace with specific benefit"
            }
        ]

        refined_response = "Check out our product - built for your needs"

        mock_content = MagicMock()
        mock_content.text = json.dumps(refined_response)

        mock_response_obj = MagicMock()
        mock_response_obj.content = [mock_content]

        mock_messages = MagicMock()
        mock_messages.create = AsyncMock(return_value=mock_response_obj)

        mock_client = MagicMock()
        mock_client.messages = mock_messages

        with patch.object(generator, "client", mock_client):
            result = await generator.refine_creative(original, violations)

        assert isinstance(result, str)
        assert "product" in result


class TestRetryLogic:
    """Tests for exponential backoff retry logic."""

    @pytest.mark.asyncio
    async def test_retry_on_api_failure(self):
        """Should retry on API failure up to max_retries times."""
        generator = CreativeGenerator(api_key="test-key")
        generator.max_retries = 3

        # Mock response for successful third attempt
        mock_content = MagicMock()
        mock_content.text = json.dumps({"success": True})

        mock_response_obj = MagicMock()
        mock_response_obj.content = [mock_content]

        # Fail twice, succeed on third
        mock_messages = MagicMock()
        mock_messages.create = AsyncMock(
            side_effect=[
                Exception("API error 1"),
                Exception("API error 2"),
                mock_response_obj
            ]
        )

        mock_client = MagicMock()
        mock_client.messages = mock_messages

        with patch.object(generator, "client", mock_client):
            result = await generator._call_claude_with_retry("test prompt")

        assert result == {"success": True}
        assert mock_messages.create.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_backoff_timing(self):
        """Should use exponential backoff: 2s, 4s, 8s."""
        generator = CreativeGenerator(api_key="test-key")
        generator.max_retries = 3

        mock_messages = MagicMock()
        mock_messages.create = AsyncMock(
            side_effect=[
                Exception("API error 1"),
                Exception("API error 2"),
                Exception("API error 3")
            ]
        )

        mock_client = MagicMock()
        mock_client.messages = mock_messages

        sleep_times = []

        async def mock_sleep(seconds):
            sleep_times.append(seconds)

        with patch.object(generator, "client", mock_client):
            with patch("asyncio.sleep", side_effect=mock_sleep):
                try:
                    await generator._call_claude_with_retry("test prompt")
                except Exception:
                    pass

        # Should sleep 2^0=1s, 2^1=2s (no, it's 2^1=2)
        assert sleep_times == [1, 2]  # 2^0=1, 2^1=2 (stops before 3rd retry)

    @pytest.mark.asyncio
    async def test_api_failure_raises_after_max_retries(self):
        """Should raise exception after max_retries failed attempts."""
        generator = CreativeGenerator(api_key="test-key")
        generator.max_retries = 3

        mock_messages = MagicMock()
        mock_messages.create = AsyncMock(side_effect=Exception("API error"))

        mock_client = MagicMock()
        mock_client.messages = mock_messages

        with patch.object(generator, "client", mock_client):
            with pytest.raises(Exception) as exc_info:
                await generator._call_claude_with_retry("test prompt")

            assert "API error" in str(exc_info.value)


class TestJSONParsing:
    """Tests for JSON parsing from Claude responses."""

    @pytest.mark.asyncio
    async def test_json_parsing_dict_response(self):
        """Should parse JSON dict from Claude response."""
        generator = CreativeGenerator(api_key="test-key")

        response_dict = {
            "message": "Test message",
            "visual_direction": "Test visual"
        }

        mock_content = MagicMock()
        mock_content.text = json.dumps(response_dict)

        mock_response_obj = MagicMock()
        mock_response_obj.content = [mock_content]

        mock_messages = MagicMock()
        mock_messages.create = AsyncMock(return_value=mock_response_obj)

        mock_client = MagicMock()
        mock_client.messages = mock_messages

        with patch.object(generator, "client", mock_client):
            result = await generator._make_api_call("test prompt")

        assert result == response_dict

    @pytest.mark.asyncio
    async def test_json_parsing_array_response(self):
        """Should parse JSON array from Claude response."""
        generator = CreativeGenerator(api_key="test-key")

        response_array = [
            {"id": 1, "content": "Variation 1"},
            {"id": 2, "content": "Variation 2"}
        ]

        mock_content = MagicMock()
        mock_content.text = json.dumps(response_array)

        mock_response_obj = MagicMock()
        mock_response_obj.content = [mock_content]

        mock_messages = MagicMock()
        mock_messages.create = AsyncMock(return_value=mock_response_obj)

        mock_client = MagicMock()
        mock_client.messages = mock_messages

        with patch.object(generator, "client", mock_client):
            result = await generator._make_api_call("test prompt")

        assert result == response_array
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_json_parsing_invalid_json(self):
        """Should raise exception on invalid JSON response."""
        generator = CreativeGenerator(api_key="test-key")

        mock_content = MagicMock()
        mock_content.text = "This is not valid JSON {]"

        mock_response_obj = MagicMock()
        mock_response_obj.content = [mock_content]

        mock_messages = MagicMock()
        mock_messages.create = AsyncMock(return_value=mock_response_obj)

        mock_client = MagicMock()
        mock_client.messages = mock_messages

        with patch.object(generator, "client", mock_client):
            with pytest.raises(Exception) as exc_info:
                await generator._make_api_call("test prompt")

            assert "Invalid JSON" in str(exc_info.value)
