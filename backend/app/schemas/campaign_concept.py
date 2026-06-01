"""Campaign Concept schema for AGT-03 output."""

from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AudienceSegmentation(BaseModel):
    """Audience segmentation for a campaign."""
    primary: str = Field(..., description="Primary target segment")
    secondary: str = Field(..., description="Secondary target segment")
    tertiary: str = Field(..., description="Tertiary target segment")


class ChannelRecommendation(BaseModel):
    """Channel recommendation with rationale and competitor gap analysis."""
    channel: str = Field(..., description="Channel name (e.g., 'TikTok', 'Email', 'LinkedIn')")
    rationale: str = Field(..., description="Why this channel aligns with audience")
    competitor_gap: str = Field(..., description="Why this is a gap vs competitors")


class MessageArchitecture(BaseModel):
    """Message architecture with master message and channel adaptations."""
    master_message: str = Field(..., description="Core campaign message")
    channel_adaptations: dict[str, str] = Field(
        ...,
        description="Channel-specific message adaptations (e.g., {'TikTok': '...', 'Email': '...'})"
    )


class CampaignPhasing(BaseModel):
    """Campaign phasing across awareness, engagement, and conversion."""
    awareness: str = Field(..., description="Awareness phase tactics and timeline")
    engagement: str = Field(..., description="Engagement phase tactics and timeline")
    conversion: str = Field(..., description="Conversion phase tactics and timeline")


class ToneBoard(BaseModel):
    """Tone board with 5 adjectives and visual direction."""
    adjectives: list[str] = Field(..., min_items=5, max_items=5, description="5 adjectives defining tone")
    visual_direction: str = Field(..., description="Visual style, color palette, design direction")


class RiskFlags(BaseModel):
    """Risk assessment flags for legal, regulatory, and sensitivity concerns."""
    legal: str | None = Field(None, description="Legal risk (e.g., unsubstantiated claims, IP issues)")
    regulatory: str | None = Field(None, description="Regulatory risk (e.g., geo compliance, data privacy)")
    sensitivity: str | None = Field(None, description="Sensitivity risk (e.g., offensive targeting, controversial)")


class CampaignConcept(BaseModel):
    """Complete campaign concept with all strategic components."""
    id: UUID = Field(default_factory=uuid4, description="Unique campaign ID")
    name: str = Field(..., description="Campaign name")
    tagline: str = Field(..., description="Campaign tagline")
    strategic_narrative: str = Field(..., description="1-2 sentences explaining why this exploits competitor gaps")
    campaign_theme: str = Field(..., description="Campaign theme")
    audience_segmentation: AudienceSegmentation = Field(..., description="Primary/secondary/tertiary segments")
    channel_mix: list[ChannelRecommendation] = Field(..., min_items=1, description="List of recommended channels")
    message_architecture: MessageArchitecture = Field(..., description="Master message + channel adaptations")
    campaign_phasing: CampaignPhasing = Field(..., description="Awareness/engagement/conversion phasing")
    tone_board: ToneBoard = Field(..., description="5 adjectives + visual direction")
    risk_flags: RiskFlags = Field(default_factory=RiskFlags, description="Legal/regulatory/sensitivity risks")
    mandate_fit_score: int = Field(..., ge=1, le=10, description="Mandate fit score (1-10)")
    gap_exploitation_score: int = Field(..., ge=1, le=10, description="Gap exploitation score (1-10)")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "TikTok Gen-Z",
                "tagline": "Where Gen-Z discovers authenticity",
                "strategic_narrative": "Competitors ignore TikTok; we dominate with authentic, youth-first positioning.",
                "campaign_theme": "Authenticity Wins",
                "audience_segmentation": {
                    "primary": "Gen-Z (16-24) urban, mobile-first",
                    "secondary": "Millennial early adopters",
                    "tertiary": "Gen-X curious about youth trends"
                },
                "channel_mix": [
                    {
                        "channel": "TikTok",
                        "rationale": "Primary audience native to platform",
                        "competitor_gap": "Competitors absent or inauthentic"
                    }
                ],
                "message_architecture": {
                    "master_message": "Real stories, real people, real impact",
                    "channel_adaptations": {
                        "TikTok": "30-second storytelling format with trending sounds"
                    }
                },
                "campaign_phasing": {
                    "awareness": "Week 1-2: Seed with influencer partnerships",
                    "engagement": "Week 3-6: User-generated content contests",
                    "conversion": "Week 7-12: Product placement + direct calls-to-action"
                },
                "tone_board": {
                    "adjectives": ["authentic", "bold", "witty", "inclusive", "innovative"],
                    "visual_direction": "Bright, desaturated colors; hand-drawn graphics; TikTok native formats"
                },
                "risk_flags": {
                    "legal": None,
                    "regulatory": None,
                    "sensitivity": None
                },
                "mandate_fit_score": 9,
                "gap_exploitation_score": 10
            }
        }
