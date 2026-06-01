"""Unit tests for Validator in Creative Director Agent (AGT-06)."""

from backend.app.agents.creative_director.models import (
    Copy,
    ImagePrompt,
    VideoConcept,
    VideoConceptScene,
)
from backend.app.agents.creative_director.validator import Validator


class TestValidator:
    """Tests for Validator class."""

    def test_validate_copy_valid(self, brand_guidelines):
        """Test that valid copy passes validation."""
        validator = Validator()
        copy = Copy(
            content="Learn More about our platform today!",
            character_count=39,
            tone="professional",
        )
        result = validator.validate_copy(copy, "instagram", brand_guidelines.model_dump())
        assert result.status == "passed"
        assert len(result.violations) == 0

    def test_validate_copy_exceeds_char_limit(self, brand_guidelines):
        """Test that copy exceeding platform character limit fails."""
        validator = Validator()
        # Instagram max is 2200 chars for main copy
        copy = Copy(
            content="x" * 2201,
            character_count=2201,
            tone="professional",
        )
        result = validator.validate_copy(copy, "instagram", brand_guidelines.model_dump())
        assert result.status == "failed"
        assert len(result.violations) > 0
        assert any(v.get("rule") == "character_limit" for v in result.violations)

    def test_validate_copy_missing_mandatory_cta(self, brand_guidelines):
        """Test that copy missing mandatory CTA fails."""
        validator = Validator()
        copy = Copy(
            content="This is some copy without a call to action.",
            character_count=44,
            tone="professional",
        )
        result = validator.validate_copy(copy, "instagram", brand_guidelines.model_dump())
        assert result.status == "failed"
        assert any(v.get("rule") == "missing_cta" for v in result.violations)

    def test_validate_tone_compliance(self, brand_guidelines):
        """Test that mismatched tone fails validation."""
        validator = Validator()
        copy = Copy(
            content="Yo! Check out our rad new product, dude!",
            character_count=41,
            tone="casual-slang",  # Doesn't match "professional yet approachable"
        )
        result = validator.validate_tone(copy, brand_guidelines.tone)
        assert result.status == "failed"
        assert any(v.get("rule") == "tone_mismatch" for v in result.violations)

    def test_platform_constraints_instagram(self):
        """Test that Instagram constraints are returned correctly."""
        validator = Validator()
        constraints = validator.get_platform_constraints("instagram")
        assert constraints["max_chars"] == 2200
        assert constraints["max_chars_caption"] == 150
        assert constraints["optimal_ratio"] == "1:1"

    def test_platform_constraints_linkedin(self):
        """Test that LinkedIn constraints are returned correctly."""
        validator = Validator()
        constraints = validator.get_platform_constraints("linkedin")
        assert constraints["max_chars"] == 3000
        assert constraints["optimal_ratio"] == "1.91:1"

    def test_platform_constraints_youtube(self):
        """Test that YouTube constraints are returned correctly."""
        validator = Validator()
        constraints = validator.get_platform_constraints("youtube")
        assert constraints["max_chars_title"] == 100
        assert constraints["max_chars_description"] == 5000

    def test_validate_image_prompt(self):
        """Test image prompt validation."""
        validator = Validator()
        # Valid prompt
        prompt = ImagePrompt(prompt="A modern dashboard with data visualizations and team collaboration")
        result = validator.validate_image_prompt(prompt, "instagram")
        assert result.status == "passed"

        # Too short prompt
        prompt_short = ImagePrompt(prompt="Short")
        result = validator.validate_image_prompt(prompt_short, "instagram")
        assert result.status == "failed"
        assert any(v.get("rule") == "prompt_too_short" for v in result.violations)

        # Empty prompt
        prompt_empty = ImagePrompt(prompt="")
        result = validator.validate_image_prompt(prompt_empty, "instagram")
        assert result.status == "failed"

    def test_validate_video_concept(self):
        """Test video concept validation."""
        validator = Validator()
        # Valid video
        video = VideoConcept(
            title="Product Demo",
            hook="See how our product transforms operations",
            shots=[
                VideoConceptScene(
                    duration_seconds=3.0,
                    description="Opening scene with team collaboration"
                ),
                VideoConceptScene(
                    duration_seconds=5.0,
                    description="Product demo showing key features"
                ),
            ],
            duration_seconds=8.0,
        )
        result = validator.validate_video_concept(video, "youtube")
        assert result.status == "passed"

        # Video with no shots
        video_no_shots = VideoConcept(
            title="Empty Video",
            hook="Hook text",
            shots=[],
            duration_seconds=0.0,
        )
        result = validator.validate_video_concept(video_no_shots, "youtube")
        assert result.status == "failed"
        assert any(v.get("rule") == "no_shots" for v in result.violations)

        # Video with unreasonable duration
        video_long = VideoConcept(
            title="Too Long",
            hook="Hook text",
            shots=[
                VideoConceptScene(
                    duration_seconds=500.0,
                    description="Way too long"
                )
            ],
            duration_seconds=500.0,
        )
        result = validator.validate_video_concept(video_long, "youtube")
        assert result.status == "failed"
        assert any(v.get("rule") == "duration_exceeds_limit" for v in result.violations)
