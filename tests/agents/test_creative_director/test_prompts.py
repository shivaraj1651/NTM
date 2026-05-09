"""Tests for Creative Director Agent prompt templates (AGT-06)."""

import pytest
import json
from backend.app.agents.creative_director.prompts import CreativePrompts


class TestCoreConceptPrompt:
    """Tests for core_concept_prompt method."""

    def test_core_concept_prompt_structure(self, campaign_input):
        """Verify prompt includes key sections (objectives, audience, JSON)."""
        prompt = CreativePrompts.core_concept_prompt(campaign_input)

        # Verify it's a string
        assert isinstance(prompt, str)
        assert len(prompt) > 0

        # Verify key sections are present
        assert "objective" in prompt.lower()
        assert "audience" in prompt.lower()
        assert "json" in prompt.lower()
        assert "message" in prompt.lower()
        assert "visual" in prompt.lower()
        assert "audio" in prompt.lower() or "direction" in prompt.lower()
        assert "tone" in prompt.lower()

        # Verify specific content from campaign_input is included
        assert campaign_input.brand_guidelines.tone in prompt
        assert campaign_input.campaign_theme in prompt
        assert campaign_input.product_details in prompt

    def test_core_concept_prompt_json_structure(self, campaign_input):
        """Verify prompt asks for structured JSON output with required fields."""
        prompt = CreativePrompts.core_concept_prompt(campaign_input)

        # Should request JSON format
        assert "{" in prompt and "}" in prompt
        # Should mention the required output fields
        assert "message" in prompt.lower()
        assert "visual_direction" in prompt.lower() or "visual direction" in prompt.lower()


class TestPlatformSpecificPrompt:
    """Tests for platform_specific_prompt method."""

    @pytest.mark.parametrize("platform,creative_type", [
        ("instagram", "copy"),
        ("linkedin", "copy"),
        ("youtube", "video_concept"),
        ("meta_ads", "copy"),
        ("tiktok", "copy"),
    ])
    def test_platform_specific_prompt_structure(self, campaign_input, platform, creative_type):
        """Verify platform guidance included in prompt."""
        core_concept = {
            "message": "Test message",
            "visual_direction": "Test visual",
            "audio_direction": "Test audio",
            "tone": "professional"
        }

        prompt = CreativePrompts.platform_specific_prompt(
            core_concept=core_concept,
            platform=platform,
            campaign_input=campaign_input,
            creative_type=creative_type
        )

        # Verify it's a string
        assert isinstance(prompt, str)
        assert len(prompt) > 0

        # Verify platform name is mentioned
        assert platform in prompt.lower()

        # Verify creative type is mentioned
        assert creative_type in prompt.lower()

        # Verify core concept is referenced
        assert core_concept["message"] in prompt

    def test_platform_specific_instagram_guidance(self, campaign_input):
        """Verify Instagram-specific guidance (visual-first)."""
        core_concept = {
            "message": "Test",
            "visual_direction": "Test",
            "audio_direction": "Test",
            "tone": "casual"
        }

        prompt = CreativePrompts.platform_specific_prompt(
            core_concept=core_concept,
            platform="instagram",
            campaign_input=campaign_input,
            creative_type="copy"
        )

        # Should emphasize visual nature of Instagram
        assert "visual" in prompt.lower() or "image" in prompt.lower()
        assert "instagram" in prompt.lower()

    def test_platform_specific_linkedin_guidance(self, campaign_input):
        """Verify LinkedIn-specific guidance (professional/B2B)."""
        core_concept = {
            "message": "Test",
            "visual_direction": "Test",
            "audio_direction": "Test",
            "tone": "professional"
        }

        prompt = CreativePrompts.platform_specific_prompt(
            core_concept=core_concept,
            platform="linkedin",
            campaign_input=campaign_input,
            creative_type="copy"
        )

        # Should emphasize professional nature
        assert "professional" in prompt.lower() or "b2b" in prompt.lower() or "business" in prompt.lower()
        assert "linkedin" in prompt.lower()

    def test_platform_specific_youtube_guidance(self, campaign_input):
        """Verify YouTube-specific guidance (storytelling)."""
        core_concept = {
            "message": "Test",
            "visual_direction": "Test",
            "audio_direction": "Test",
            "tone": "engaging"
        }

        prompt = CreativePrompts.platform_specific_prompt(
            core_concept=core_concept,
            platform="youtube",
            campaign_input=campaign_input,
            creative_type="video_concept"
        )

        # Should emphasize storytelling
        assert "story" in prompt.lower() or "narrative" in prompt.lower() or "hook" in prompt.lower()
        assert "youtube" in prompt.lower()

    def test_platform_specific_includes_variations(self, campaign_input):
        """Verify prompt asks for 2-3 variations."""
        core_concept = {
            "message": "Test",
            "visual_direction": "Test",
            "audio_direction": "Test",
            "tone": "professional"
        }

        prompt = CreativePrompts.platform_specific_prompt(
            core_concept=core_concept,
            platform="linkedin",
            campaign_input=campaign_input,
            creative_type="copy"
        )

        # Should request multiple variations
        assert "2" in prompt or "3" in prompt or "variation" in prompt.lower()


class TestRefinementPrompt:
    """Tests for refinement_prompt method."""

    def test_refinement_prompt_structure(self):
        """Verify original content and violations included in prompt."""
        original_creative = "Learn more about our product and schedule a demo today!"
        violations = [
            {
                "rule": "messaging_rules",
                "severity": "high",
                "message": "Missing company name",
                "suggestion": "Add 'TechCorp' to the copy"
            },
            {
                "rule": "mandatory_ctas",
                "severity": "medium",
                "message": "Missing 'Get Started' CTA",
                "suggestion": "Include 'Get Started' as alternative CTA"
            }
        ]

        prompt = CreativePrompts.refinement_prompt(
            original_creative=original_creative,
            violations=violations
        )

        # Verify it's a string
        assert isinstance(prompt, str)
        assert len(prompt) > 0

        # Verify original creative is included
        assert original_creative in prompt

        # Verify violations are included
        for violation in violations:
            assert violation["rule"] in prompt
            assert violation["message"] in prompt
            assert violation["suggestion"] in prompt

    def test_refinement_prompt_with_multiple_violations(self):
        """Verify prompt handles multiple violations."""
        original_creative = "Buy now!"
        violations = [
            {
                "rule": "brand_tone",
                "severity": "high",
                "message": "Tone is too aggressive",
                "suggestion": "Use 'professional yet approachable' tone"
            },
            {
                "rule": "character_limit",
                "severity": "medium",
                "message": "Too short for LinkedIn",
                "suggestion": "Expand to 100-150 characters with value proposition"
            },
            {
                "rule": "mandatory_ctas",
                "severity": "high",
                "message": "Missing mandatory CTA",
                "suggestion": "Add 'Schedule Demo' or 'Learn More'"
            }
        ]

        prompt = CreativePrompts.refinement_prompt(
            original_creative=original_creative,
            violations=violations
        )

        # All violations should be present
        assert len(violations) == 3
        for violation in violations:
            assert violation["rule"] in prompt

    def test_refinement_prompt_severity_emphasis(self):
        """Verify violations with high severity are emphasized."""
        original_creative = "Check this out"
        violations = [
            {
                "rule": "test",
                "severity": "high",
                "message": "Critical issue",
                "suggestion": "Fix this immediately"
            }
        ]

        prompt = CreativePrompts.refinement_prompt(
            original_creative=original_creative,
            violations=violations
        )

        # Severity should be reflected in the prompt
        assert "high" in prompt.lower() or "critical" in prompt.lower() or "must" in prompt.lower()
