"""Validation engine for Creative Director Agent (AGT-06).

Validates generated creatives against brand guidelines and platform constraints.
"""

from typing import Any

from backend.app.agents.creative_director.models import (
    Copy,
    CreativeValidation,
    ImagePrompt,
    VideoConcept,
)


class Validator:
    """Validates creatives against brand guidelines and platform constraints."""

    # Platform constraints dictionary
    PLATFORM_CONSTRAINTS = {
        "instagram": {
            "max_chars": 2200,
            "max_chars_caption": 150,
            "optimal_ratio": "1:1",
            "supported_formats": ["image", "video", "carousel"],
            "max_video_duration": 60,  # seconds
        },
        "linkedin": {
            "max_chars": 3000,
            "optimal_ratio": "1.91:1",
            "supported_formats": ["image", "video", "document"],
            "max_video_duration": 600,
        },
        "youtube": {
            "max_chars_title": 100,
            "max_chars_description": 5000,
            "optimal_ratio": "16:9",
            "supported_formats": ["video"],
            "max_video_duration": 120,  # Up to 2 hours, but typically much shorter
        },
        "meta_ads": {
            "max_chars_primary": 125,
            "max_chars_description": 30,
            "optimal_ratio": "1.2:1",
            "supported_formats": ["image", "video"],
            "max_video_duration": 120,
        },
        "tiktok": {
            "max_chars_caption": 150,
            "optimal_ratio": "9:16",
            "supported_formats": ["video"],
            "max_video_duration": 60,
        },
    }

    # Tone compatibility mapping
    TONE_COMPATIBILITY = {
        "professional": ["formal", "corporate", "professional"],
        "casual": ["friendly", "conversational", "casual", "informal"],
        "humorous": ["funny", "witty", "humorous", "comedic"],
        "formal": ["professional", "formal", "corporate"],
        "friendly": ["casual", "conversational", "friendly"],
        "corporate": ["professional", "formal", "corporate"],
    }

    def validate_copy(
        self,
        copy: Copy,
        platform: str,
        brand_rules: dict[str, Any],
    ) -> CreativeValidation:
        """Validate copy against platform constraints and brand guidelines.

        Args:
            copy: Copy object to validate
            platform: Target platform (instagram, linkedin, etc.)
            brand_rules: Brand guidelines as dict

        Returns:
            CreativeValidation with status and violations
        """
        violations = []
        warnings = []

        if platform not in self.PLATFORM_CONSTRAINTS:
            violations.append({
                "rule": "invalid_platform",
                "severity": "error",
                "message": f"Unknown platform: {platform}",
                "suggestion": f"Use one of: {', '.join(self.PLATFORM_CONSTRAINTS.keys())}",
            })
            return CreativeValidation(status="failed", violations=violations, warnings=warnings)

        constraints = self.PLATFORM_CONSTRAINTS[platform]

        # Check character limit
        max_chars = constraints.get("max_chars")
        if max_chars and copy.character_count > max_chars:
            violations.append({
                "rule": "character_limit",
                "severity": "error",
                "message": f"Copy exceeds {max_chars} character limit for {platform} (got {copy.character_count})",
                "suggestion": "Shorten copy to meet platform character limits",
            })

        # Check for mandatory CTAs
        if brand_rules and "mandatory_ctas" in brand_rules:
            mandatory_ctas = brand_rules["mandatory_ctas"]
            content_lower = copy.content.lower()
            found_cta = False

            for cta in mandatory_ctas:
                if cta.lower() in content_lower:
                    found_cta = True
                    break

            if not found_cta and mandatory_ctas:
                violations.append({
                    "rule": "missing_cta",
                    "severity": "error",
                    "message": f"Copy must include at least one of: {', '.join(mandatory_ctas)}",
                    "suggestion": f"Add one of the mandatory CTAs: {', '.join(mandatory_ctas)}",
                })

        status = "failed" if violations else "passed"
        return CreativeValidation(status=status, violations=violations, warnings=warnings)

    def validate_tone(
        self,
        copy: Copy,
        brand_tone: str,
    ) -> CreativeValidation:
        """Validate that copy tone matches brand tone.

        Args:
            copy: Copy object to validate
            brand_tone: Expected brand tone

        Returns:
            CreativeValidation with status and violations
        """
        violations = []
        warnings = []

        # Check if copy tone is compatible with brand tone
        brand_tone_lower = brand_tone.lower()
        copy_tone_lower = copy.tone.lower()

        # Get compatible tones for the brand
        compatible_tones = self.TONE_COMPATIBILITY.get(
            brand_tone_lower,
            [brand_tone_lower]
        )

        # Check if copy tone is compatible
        is_compatible = False
        for compatible in compatible_tones:
            if compatible in copy_tone_lower or copy_tone_lower in compatible:
                is_compatible = True
                break

        if not is_compatible:
            violations.append({
                "rule": "tone_mismatch",
                "severity": "warning",
                "message": f"Copy tone '{copy.tone}' does not match brand tone '{brand_tone}'",
                "suggestion": f"Adjust tone to match brand guidelines (expected: {brand_tone})",
            })

        status = "failed" if violations else "passed"
        return CreativeValidation(status=status, violations=violations, warnings=warnings)

    def validate_image_prompt(
        self,
        prompt: ImagePrompt,
        platform: str,
    ) -> CreativeValidation:
        """Validate image generation prompt.

        Args:
            prompt: ImagePrompt object to validate
            platform: Target platform

        Returns:
            CreativeValidation with status and violations
        """
        violations = []
        warnings = []

        # Check if prompt is empty
        if not prompt.prompt or not prompt.prompt.strip():
            violations.append({
                "rule": "empty_prompt",
                "severity": "error",
                "message": "Image prompt cannot be empty",
                "suggestion": "Provide a detailed image description for generation",
            })
        # Check minimum length
        elif len(prompt.prompt.strip()) < 20:
            violations.append({
                "rule": "prompt_too_short",
                "severity": "error",
                "message": "Image prompt must be at least 20 characters long",
                "suggestion": "Add more details to the image prompt (at least 20 characters)",
            })

        status = "failed" if violations else "passed"
        return CreativeValidation(status=status, violations=violations, warnings=warnings)

    def validate_video_concept(
        self,
        video: VideoConcept,
        platform: str,
    ) -> CreativeValidation:
        """Validate video concept against platform constraints.

        Args:
            video: VideoConcept object to validate
            platform: Target platform

        Returns:
            CreativeValidation with status and violations
        """
        violations = []
        warnings = []

        if platform not in self.PLATFORM_CONSTRAINTS:
            violations.append({
                "rule": "invalid_platform",
                "severity": "error",
                "message": f"Unknown platform: {platform}",
                "suggestion": f"Use one of: {', '.join(self.PLATFORM_CONSTRAINTS.keys())}",
            })
            return CreativeValidation(status="failed", violations=violations, warnings=warnings)

        constraints = self.PLATFORM_CONSTRAINTS[platform]

        # Check if video has at least one shot
        if not video.shots or len(video.shots) == 0:
            violations.append({
                "rule": "no_shots",
                "severity": "error",
                "message": "Video concept must have at least one shot",
                "suggestion": "Add at least one shot/scene to the video concept",
            })

        # Check duration
        max_duration = constraints.get("max_video_duration", 120)
        if video.duration_seconds > max_duration:
            violations.append({
                "rule": "duration_exceeds_limit",
                "severity": "error",
                "message": f"Video duration ({video.duration_seconds}s) exceeds platform limit ({max_duration}s)",
                "suggestion": f"Reduce video duration to {max_duration} seconds or less",
            })

        # Warn if duration is very short
        if video.duration_seconds < 3:
            warnings.append(f"Video is very short ({video.duration_seconds}s) - may not be effective")

        status = "failed" if violations else "passed"
        return CreativeValidation(status=status, violations=violations, warnings=warnings)

    def get_platform_constraints(self, platform: str) -> dict[str, Any]:
        """Get platform-specific constraints.

        Args:
            platform: Target platform

        Returns:
            Dictionary of platform constraints
        """
        return self.PLATFORM_CONSTRAINTS.get(platform, {})
