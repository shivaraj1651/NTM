"""Data models and schemas for Creative Director Agent (AGT-06)."""

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    """Return current UTC time with timezone info."""
    return datetime.now(UTC)


# Input Models
class BrandGuidelines(BaseModel):
    """Brand guidelines that must be followed in generated creatives."""

    tone: str = Field(..., description="Brand voice/tone (e.g., 'professional', 'casual', 'humorous')")
    colors: list[str] = Field(..., description="Brand color palette")
    messaging_rules: list[str] = Field(..., description="Mandatory messaging requirements")
    mandatory_ctas: list[str] = Field(..., description="Required calls-to-action")
    visual_style: str | None = None
    tagline: str | None = None


class TargetAudience(BaseModel):
    """Target audience demographics and psychographics."""

    demographics: dict[str, str] | None = None
    psychographics: dict[str, str] | None = None
    segments: list[str] | None = None
    language: str = "en"


class CampaignInput(BaseModel):
    """Campaign input with all context needed for creative generation."""

    campaign_id: str = Field(..., description="Campaign UUID")
    tenant_id: str = Field(..., description="Tenant UUID")
    objectives: list[str] = Field(..., description="Campaign objectives/KPIs")
    target_audience: TargetAudience
    brand_guidelines: BrandGuidelines
    platforms: list[Literal["instagram", "linkedin", "youtube", "meta_ads", "tiktok", "twitter"]] = Field(
        ..., description="Target platforms"
    )
    budget_allocation: dict[str, float] | None = None
    product_details: str = Field(..., description="Product/service description")
    campaign_theme: str = Field(..., description="Campaign narrative/angle")
    primary_cta: str = Field(..., description="Primary call-to-action")
    competitor_insights: str | None = None
    optional_assets: list[dict[str, str]] | None = None  # {url, type, description}
    channel_allocation: dict[str, float] | None = None  # e.g., {"instagram": 0.4, "linkedin": 0.3}


# Creative Models
class CreativeValidation(BaseModel):
    """Validation result for generated creative content."""

    status: Literal["passed", "failed"]
    violations: list[dict[str, str]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ImagePrompt(BaseModel):
    """Image generation prompt for visual content."""

    prompt: str = Field(..., description="DALL-E style prompt")
    style: str | None = None
    validation: CreativeValidation = Field(default_factory=lambda: CreativeValidation(status="passed"))


class VideoConceptScene(BaseModel):
    """Individual scene in a video concept."""

    duration_seconds: float
    description: str
    notes: str | None = None


class VideoConcept(BaseModel):
    """Video storyboard and concept."""

    title: str
    hook: str = Field(..., description="Opening hook (first 3 seconds)")
    shots: list[VideoConceptScene]
    pacing_notes: str | None = None
    duration_seconds: float
    validation: CreativeValidation = Field(default_factory=lambda: CreativeValidation(status="passed"))


class Copy(BaseModel):
    """Marketing copy/ad text."""

    content: str
    character_count: int
    tone: str
    validation: CreativeValidation = Field(default_factory=lambda: CreativeValidation(status="passed"))


class VoiceoverScript(BaseModel):
    """Voiceover script for audio content."""

    script: str
    duration_seconds: float | None = None
    tone: str
    pacing: str | None = None
    validation: CreativeValidation = Field(default_factory=lambda: CreativeValidation(status="passed"))


class PlatformCreatives(BaseModel):
    """Collection of creatives for a specific platform."""

    platform: str
    copy: list[Copy] = Field(default_factory=list)
    image_prompts: list[ImagePrompt] = Field(default_factory=list)
    video_concepts: list[VideoConcept] = Field(default_factory=list)
    voiceover_scripts: list[VoiceoverScript] = Field(default_factory=list)
    captions: list[Copy] = Field(default_factory=list)


# Output Models
class CoreConcept(BaseModel):
    """Core creative concept that unifies all platform variations."""

    message: str
    visual_direction: str
    audio_direction: str | None = None
    tone: str


class GenerationMetadata(BaseModel):
    """Metadata about the generation process."""

    core_concept: CoreConcept
    validation_status: Literal["passed", "failed", "partial"]
    validation_summary: str | None = None
    refinement_attempts: int = 0
    generation_time_ms: float = 0.0
    model_used: str = "claude-opus-4-7"
    errors: list[str] = Field(default_factory=list)


class CreativeDirectorOutput(BaseModel):
    """Final output from Creative Director Agent."""

    campaign_id: str
    generation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    generated_at: datetime = Field(default_factory=utc_now)
    platforms: dict[str, PlatformCreatives]
    metadata: GenerationMetadata
    error: dict[str, str] | None = None
