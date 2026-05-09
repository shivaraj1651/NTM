"""Validation engine for Creative Director Agent (AGT-06).

Validates generated creatives against brand guidelines and platform constraints.
"""

from typing import Dict, List, Any
from backend.app.agents.creative_director.models import (
    Copy,
    ImagePrompt,
    VideoConcept,
    CreativeValidation,
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
        brand_rules: Dict[str, Any],
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
                "type": "PLATFORM_ERROR",
                "message": f"Unknown platform: {platform}",
            })
            return CreativeValidation(status="failed", violations=violations, warnings=warnings)

        constraints = self.PLATFORM_CONSTRAINTS[platform]

        # Check character limit
        max_chars = constraints.get("max_chars")
        if max_chars and copy.character_count > max_chars:
            violations.append({
                "type": "CHARACTER_LIMIT_EXCEEDED",
                "message": f"Copy exceeds {max_chars} character limit for {platform} (got {copy.character_count})",
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
                    "type": "MISSING_MANDATORY_CTA",
                    "message": f"Copy must include at least one of: {', '.join(mandatory_ctas)}",
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
                "type": "TONE_MISMATCH",
                "message": f"Copy tone '{copy.tone}' does not match brand tone '{brand_tone}'",
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
                "type": "EMPTY_PROMPT",
                "message": "Image prompt cannot be empty",
            })
        # Check minimum length
        elif len(prompt.prompt.strip()) < 20:
            violations.append({
                "type": "PROMPT_TOO_SHORT",
                "message": "Image prompt must be at least 20 characters long",
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
                "type": "PLATFORM_ERROR",
                "message": f"Unknown platform: {platform}",
            })
            return CreativeValidation(status="failed", violations=violations, warnings=warnings)

        constraints = self.PLATFORM_CONSTRAINTS[platform]

        # Check if video has at least one shot
        if not video.shots or len(video.shots) == 0:
            violations.append({
                "type": "NO_SHOTS",
                "message": "Video concept must have at least one shot",
            })

        # Check duration
        max_duration = constraints.get("max_video_duration", 120)
        if video.duration_seconds > max_duration:
            violations.append({
                "type": "DURATION_EXCEEDS_LIMIT",
                "message": f"Video duration ({video.duration_seconds}s) exceeds platform limit ({max_duration}s)",
            })

        # Warn if duration is very short
        if video.duration_seconds < 3:
            warnings.append(f"Video is very short ({video.duration_seconds}s) - may not be effective")

        status = "failed" if violations else "passed"
        return CreativeValidation(status=status, violations=violations, warnings=warnings)

    def get_platform_constraints(self, platform: str) -> Dict[str, Any]:
        """Get platform-specific constraints.

        Args:
            platform: Target platform

        Returns:
            Dictionary of platform constraints
        """
        return self.PLATFORM_CONSTRAINTS.get(platform, {})
