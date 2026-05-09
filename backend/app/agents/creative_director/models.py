"""Data models and schemas for Creative Director Agent (AGT-06)."""

from typing import Optional, Dict, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid


def utc_now() -> datetime:
    """Return current UTC time with timezone info."""
    return datetime.now(timezone.utc)


# Input Models
class BrandGuidelines(BaseModel):
    """Brand guidelines that must be followed in generated creatives."""

    tone: str = Field(..., description="Brand voice/tone (e.g., 'professional', 'casual', 'humorous')")
    colors: List[str] = Field(..., description="Brand color palette")
    messaging_rules: List[str] = Field(..., description="Mandatory messaging requirements")
    mandatory_ctas: List[str] = Field(..., description="Required calls-to-action")
    visual_style: Optional[str] = None
    tagline: Optional[str] = None


class TargetAudience(BaseModel):
    """Target audience demographics and psychographics."""

    demographics: Optional[Dict[str, str]] = None
    psychographics: Optional[Dict[str, str]] = None
    segments: Optional[List[str]] = None
    language: str = "en"


class CampaignInput(BaseModel):
    """Campaign input with all context needed for creative generation."""

    campaign_id: str = Field(..., description="Campaign UUID")
    tenant_id: str = Field(..., description="Tenant UUID")
    objectives: List[str] = Field(..., description="Campaign objectives/KPIs")
    target_audience: TargetAudience
    brand_guidelines: BrandGuidelines
    platforms: List[Literal["instagram", "linkedin", "youtube", "meta_ads", "tiktok", "twitter"]] = Field(
        ..., description="Target platforms"
    )
    budget_allocation: Optional[Dict[str, float]] = None
    product_details: str = Field(..., description="Product/service description")
    campaign_theme: str = Field(..., description="Campaign narrative/angle")
    primary_cta: str = Field(..., description="Primary call-to-action")
    competitor_insights: Optional[str] = None
    optional_assets: Optional[List[Dict[str, str]]] = None  # {url, type, description}
    channel_allocation: Optional[Dict[str, float]] = None  # e.g., {"instagram": 0.4, "linkedin": 0.3}


# Creative Models
class CreativeValidation(BaseModel):
    """Validation result for generated creative content."""

    status: Literal["passed", "failed"]
    violations: List[Dict[str, str]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ImagePrompt(BaseModel):
    """Image generation prompt for visual content."""

    prompt: str = Field(..., description="DALL-E style prompt")
    style: Optional[str] = None
    validation: CreativeValidation = Field(default_factory=lambda: CreativeValidation(status="passed"))


class VideoConceptScene(BaseModel):
    """Individual scene in a video concept."""

    duration_seconds: float
    description: str
    notes: Optional[str] = None


class VideoConcept(BaseModel):
    """Video storyboard and concept."""

    title: str
    hook: str = Field(..., description="Opening hook (first 3 seconds)")
    shots: List[VideoConceptScene]
    pacing_notes: Optional[str] = None
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
    duration_seconds: Optional[float] = None
    tone: str
    pacing: Optional[str] = None
    validation: CreativeValidation = Field(default_factory=lambda: CreativeValidation(status="passed"))


class PlatformCreatives(BaseModel):
    """Collection of creatives for a specific platform."""

    platform: str
    copy: List[Copy] = Field(default_factory=list)
    image_prompts: List[ImagePrompt] = Field(default_factory=list)
    video_concepts: List[VideoConcept] = Field(default_factory=list)
    voiceover_scripts: List[VoiceoverScript] = Field(default_factory=list)
    captions: List[Copy] = Field(default_factory=list)


# Output Models
class CoreConcept(BaseModel):
    """Core creative concept that unifies all platform variations."""

    message: str
    visual_direction: str
    audio_direction: Optional[str] = None
    tone: str


class GenerationMetadata(BaseModel):
    """Metadata about the generation process."""

    core_concept: CoreConcept
    validation_status: Literal["passed", "failed", "partial"]
    validation_summary: Optional[str] = None
    refinement_attempts: int = 0
    generation_time_ms: float = 0.0
    model_used: str = "claude-opus-4.7"
    errors: List[str] = Field(default_factory=list)


class CreativeDirectorOutput(BaseModel):
    """Final output from Creative Director Agent."""

    campaign_id: str
    generation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    generated_at: datetime = Field(default_factory=utc_now)
    platforms: Dict[str, PlatformCreatives]
    metadata: GenerationMetadata
    error: Optional[Dict[str, str]] = None
