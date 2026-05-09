"""Unit tests for Creative Director Agent (AGT-06) models."""

import pytest
from backend.app.agents.creative_director.models import (
    BrandGuidelines,
    CampaignInput,
    TargetAudience,
    CreativeValidation,
    Copy,
    CoreConcept,
    GenerationMetadata,
    CreativeDirectorOutput,
    ImagePrompt,
    VideoConcept,
    VideoConceptScene,
    VoiceoverScript,
    PlatformCreatives,
)


class TestBrandGuidelines:
    """Tests for BrandGuidelines model."""

    def test_brand_guidelines_valid(self):
        """Test creating valid BrandGuidelines."""
        guidelines = BrandGuidelines(
            tone="professional",
            colors=["#003366", "#FF6600"],
            messaging_rules=["Always include brand name", "Emphasize quality"],
            mandatory_ctas=["Learn More", "Contact Us"],
        )
        assert guidelines.tone == "professional"
        assert len(guidelines.colors) == 2
        assert len(guidelines.messaging_rules) == 2
        assert guidelines.visual_style is None
        assert guidelines.tagline is None

    def test_brand_guidelines_with_optional_fields(self):
        """Test BrandGuidelines with optional fields."""
        guidelines = BrandGuidelines(
            tone="casual",
            colors=["#FF0000"],
            messaging_rules=["Be fun"],
            mandatory_ctas=["Sign Up"],
            visual_style="modern, vibrant",
            tagline="Life is fun",
        )
        assert guidelines.visual_style == "modern, vibrant"
        assert guidelines.tagline == "Life is fun"


class TestTargetAudience:
    """Tests for TargetAudience model."""

    def test_target_audience_minimal(self):
        """Test TargetAudience with minimal required fields."""
        audience = TargetAudience()
        assert audience.language == "en"
        assert audience.demographics is None
        assert audience.psychographics is None
        assert audience.segments is None

    def test_target_audience_with_segments(self):
        """Test TargetAudience with segments."""
        audience = TargetAudience(
            demographics={"age": "25-45", "income": "75k-150k"},
            psychographics={"values": "innovation"},
            segments=["tech-savvy", "urban"],
            language="en",
        )
        assert len(audience.segments) == 2
        assert audience.demographics["age"] == "25-45"


class TestCampaignInput:
    """Tests for CampaignInput model."""

    def test_campaign_input_valid(self):
        """Test creating valid CampaignInput."""
        input_data = CampaignInput(
            campaign_id="camp-123",
            tenant_id="tenant-456",
            objectives=["Increase brand awareness", "Drive conversions"],
            target_audience=TargetAudience(segments=["18-25", "urban"]),
            brand_guidelines=BrandGuidelines(
                tone="casual",
                colors=["#000", "#FFF"],
                messaging_rules=["Be fun"],
                mandatory_ctas=["Sign Up"],
            ),
            platforms=["instagram", "linkedin"],
            product_details="Cool product",
            campaign_theme="Summer vibes",
            primary_cta="Shop Now",
        )
        assert input_data.campaign_id == "camp-123"
        assert len(input_data.platforms) == 2
        assert "instagram" in input_data.platforms

    def test_campaign_input_with_optional_fields(self):
        """Test CampaignInput with optional fields."""
        input_data = CampaignInput(
            campaign_id="camp-456",
            tenant_id="tenant-789",
            objectives=["Growth"],
            target_audience=TargetAudience(),
            brand_guidelines=BrandGuidelines(
                tone="professional",
                colors=["#003366"],
                messaging_rules=["Professional"],
                mandatory_ctas=["Learn More"],
            ),
            platforms=["youtube"],
            product_details="SaaS tool",
            campaign_theme="Digital transformation",
            primary_cta="Get Started",
            budget_allocation={"youtube": 1000.0},
            competitor_insights="They focus on features",
        )
        assert input_data.budget_allocation is not None
        assert input_data.competitor_insights is not None

    def test_campaign_input_all_platform_types(self):
        """Test CampaignInput with all valid platform types."""
        platforms = ["instagram", "linkedin", "youtube", "meta_ads", "tiktok", "twitter"]
        input_data = CampaignInput(
            campaign_id="camp-all",
            tenant_id="tenant-all",
            objectives=["Test"],
            target_audience=TargetAudience(),
            brand_guidelines=BrandGuidelines(
                tone="test",
                colors=["#000"],
                messaging_rules=["test"],
                mandatory_ctas=["test"],
            ),
            platforms=platforms,
            product_details="test",
            campaign_theme="test",
            primary_cta="test",
        )
        assert len(input_data.platforms) == 6
        for platform in platforms:
            assert platform in input_data.platforms


class TestCreativeValidation:
    """Tests for CreativeValidation model."""

    def test_validation_passed(self):
        """Test validation passed status."""
        validation = CreativeValidation(status="passed")
        assert validation.status == "passed"
        assert len(validation.violations) == 0
        assert len(validation.warnings) == 0

    def test_validation_failed_with_violations(self):
        """Test validation failed with violations."""
        validation = CreativeValidation(
            status="failed",
            violations=[
                {"rule": "too_long", "message": "Copy exceeds limit"},
                {"rule": "missing_cta", "message": "Missing mandatory CTA"},
            ],
            warnings=["Could be shorter"],
        )
        assert validation.status == "failed"
        assert len(validation.violations) == 2
        assert len(validation.warnings) == 1


class TestCopy:
    """Tests for Copy model."""

    def test_copy_valid(self):
        """Test creating valid Copy."""
        copy = Copy(
            content="Buy now! Learn More",
            character_count=19,
            tone="urgent",
            validation=CreativeValidation(status="passed"),
        )
        assert copy.content == "Buy now! Learn More"
        assert copy.character_count == 19
        assert copy.validation.status == "passed"

    def test_copy_with_default_validation(self):
        """Test Copy with default validation."""
        copy = Copy(
            content="Test copy",
            character_count=9,
            tone="professional",
        )
        assert copy.validation.status == "passed"


class TestImagePrompt:
    """Tests for ImagePrompt model."""

    def test_image_prompt_minimal(self):
        """Test minimal ImagePrompt."""
        prompt = ImagePrompt(
            prompt="A modern dashboard with data visualization",
        )
        assert prompt.prompt == "A modern dashboard with data visualization"
        assert prompt.style is None
        assert prompt.validation.status == "passed"

    def test_image_prompt_with_style(self):
        """Test ImagePrompt with style."""
        prompt = ImagePrompt(
            prompt="A modern dashboard with data visualization",
            style="contemporary",
        )
        assert prompt.style == "contemporary"


class TestVideoConcept:
    """Tests for VideoConcept model."""

    def test_video_concept_valid(self):
        """Test creating valid VideoConcept."""
        scenes = [
            VideoConceptScene(
                duration_seconds=3.0,
                description="Opening hook with logo",
            ),
            VideoConceptScene(
                duration_seconds=10.0,
                description="Product demo",
                notes="Show key features",
            ),
        ]
        video = VideoConcept(
            title="Product Launch",
            hook="See how it transforms your workflow",
            shots=scenes,
            duration_seconds=13.0,
        )
        assert video.title == "Product Launch"
        assert len(video.shots) == 2
        assert video.duration_seconds == 13.0


class TestVoiceoverScript:
    """Tests for VoiceoverScript model."""

    def test_voiceover_script_minimal(self):
        """Test minimal VoiceoverScript."""
        script = VoiceoverScript(
            script="Welcome to our product. It changes everything.",
            tone="warm",
        )
        assert script.script == "Welcome to our product. It changes everything."
        assert script.tone == "warm"
        assert script.duration_seconds is None

    def test_voiceover_script_full(self):
        """Test full VoiceoverScript."""
        script = VoiceoverScript(
            script="Welcome to our product.",
            duration_seconds=2.5,
            tone="professional",
            pacing="steady",
        )
        assert script.duration_seconds == 2.5
        assert script.pacing == "steady"


class TestPlatformCreatives:
    """Tests for PlatformCreatives model."""

    def test_platform_creatives_minimal(self):
        """Test minimal PlatformCreatives."""
        creatives = PlatformCreatives(platform="instagram")
        assert creatives.platform == "instagram"
        assert len(creatives.copy) == 0
        assert len(creatives.image_prompts) == 0
        assert len(creatives.video_concepts) == 0
        assert len(creatives.captions) == 0

    def test_platform_creatives_with_content(self):
        """Test PlatformCreatives with content."""
        copy_item = Copy(
            content="Check this out",
            character_count=14,
            tone="casual",
        )
        creatives = PlatformCreatives(
            platform="instagram",
            copy=[copy_item],
        )
        assert len(creatives.copy) == 1
        assert creatives.copy[0].content == "Check this out"


class TestCoreConceptAndMetadata:
    """Tests for CoreConcept and GenerationMetadata."""

    def test_core_concept_valid(self):
        """Test creating valid CoreConcept."""
        concept = CoreConcept(
            message="Transform your operations",
            visual_direction="Modern dashboards, minimal design",
            tone="professional",
        )
        assert concept.message == "Transform your operations"
        assert concept.audio_direction is None

    def test_core_concept_with_audio(self):
        """Test CoreConcept with audio direction."""
        concept = CoreConcept(
            message="Transform your operations",
            visual_direction="Modern dashboards",
            audio_direction="Professional, warm voiceover",
            tone="professional",
        )
        assert concept.audio_direction == "Professional, warm voiceover"

    def test_generation_metadata_valid(self):
        """Test creating valid GenerationMetadata."""
        concept = CoreConcept(
            message="Test",
            visual_direction="Test visual",
            tone="professional",
        )
        metadata = GenerationMetadata(
            core_concept=concept,
            validation_status="passed",
        )
        assert metadata.validation_status == "passed"
        assert metadata.refinement_attempts == 0
        assert metadata.generation_time_ms == 0.0


class TestCreativeDirectorOutput:
    """Tests for CreativeDirectorOutput model."""

    def test_output_valid(self):
        """Test creating valid CreativeDirectorOutput."""
        concept = CoreConcept(
            message="Test",
            visual_direction="Test",
            tone="professional",
        )
        metadata = GenerationMetadata(
            core_concept=concept,
            validation_status="passed",
        )
        output = CreativeDirectorOutput(
            campaign_id="camp-1",
            tenant_id="tenant-1",
            platforms={
                "instagram": PlatformCreatives(platform="instagram"),
                "linkedin": PlatformCreatives(platform="linkedin"),
            },
            metadata=metadata,
        )
        assert output.campaign_id == "camp-1"
        assert len(output.platforms) == 2
        assert "instagram" in output.platforms
        assert output.generation_id is not None
        assert output.generated_at is not None
