"""Media Plan schemas for AGT-04 output."""

from datetime import date
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ChannelEnum(str, Enum):
    """Channel type enumeration."""
    SOCIAL = "Social"
    SEARCH = "Search"
    DISPLAY = "Display"
    EMAIL = "Email"
    WHATSAPP = "WhatsApp"
    INFLUENCER = "Influencer"
    PRINT = "Print"
    OOH = "OOH"
    RADIO = "Radio"
    TV = "TV"
    EVENTS = "Events"
    CINEMA = "Cinema"
    DIRECT_MAIL = "DirectMail"


class PhaseEnum(str, Enum):
    """Campaign phase enumeration."""
    AWARENESS = "Awareness"
    ENGAGEMENT = "Engagement"
    CONVERSION = "Conversion"


class AudienceSegmentEnum(str, Enum):
    """Audience segment enumeration."""
    PRIMARY = "Primary"
    SECONDARY = "Secondary"
    TERTIARY = "Tertiary"


class Activation(BaseModel):
    """Individual media activation (placement)."""
    id: UUID = Field(default_factory=uuid4, description="Unique activation ID")
    channel_enum: ChannelEnum = Field(..., description="Channel type enum")
    sub_channel: str = Field(..., description="Specific channel name (e.g., 'TikTok', 'Google Search')")
    format: str = Field(..., description="Media format (e.g., 'Video 15s', 'Static Image')")
    geography: str = Field(..., description="Market or region (e.g., 'US', 'NYC')")
    placement: str = Field(..., description="Placement location (e.g., 'Feed', 'Search Results')")
    phase: PhaseEnum = Field(..., description="Campaign phase")
    scheduled_date: date = Field(..., description="Activation start date")
    duration: int = Field(..., ge=1, description="Duration in days")
    frequency: str = Field(..., description="Delivery frequency (e.g., '3x daily', 'weekly')")
    audience_segment: AudienceSegmentEnum = Field(..., description="Target audience segment")
    estimated_reach: int = Field(..., ge=1, description="Estimated number of people reached")
    estimated_cpm: float = Field(..., ge=0.01, description="Cost per thousand impressions")
    cost_estimated: float = Field(..., ge=0, description="Total activation cost")
    message_version_ref: str = Field(..., description="Reference to message architecture + tone board")
    lead_time_days: int | None = Field(None, ge=0, description="Production lead time for offline channels")
    offline_constraints: str | None = Field(None, description="Constraint notes for offline channels")


class PhaseBreakdown(BaseModel):
    """Budget breakdown for a single phase."""
    allocated: float = Field(..., ge=0)
    spent: float = Field(..., ge=0)
    remaining: float = Field(..., ge=0)


class ChannelSpend(BaseModel):
    """Budget breakdown for a single channel."""
    allocated: float = Field(..., ge=0)
    spent: float = Field(..., ge=0)
    activations_count: int = Field(..., ge=0)


class ContingencyBreakdown(BaseModel):
    """Contingency budget breakdown."""
    allocated: float = Field(..., ge=0)
    used: float = Field(..., ge=0)
    remaining: float = Field(..., ge=0)


class BudgetSummary(BaseModel):
    """Budget summary with phase/channel breakdown."""
    total_budget: float = Field(..., ge=0)
    currency: str = Field(..., description="Currency code (e.g., 'USD')")
    phase_breakdown: dict[str, PhaseBreakdown] = Field(
        ...,
        description="Budget breakdown by phase (Awareness, Engagement, Conversion)"
    )
    channel_breakdown: dict[str, ChannelSpend] = Field(
        ...,
        description="Budget breakdown by channel (TikTok, Google Search, etc.)"
    )
    contingency: ContingencyBreakdown = Field(..., description="Contingency budget details")
    total_spent: float = Field(..., ge=0, description="Total activation costs")
    total_remaining: float = Field(..., ge=0, description="Unallocated budget")
    utilization_pct: float = Field(..., ge=0, le=100, description="Budget utilization percentage")


class MediaPlanResponse(BaseModel):
    """Full media planner agent response."""
    activations: list[Activation] = Field(..., description="List of generated activations")
    budget_summary: BudgetSummary = Field(..., description="Budget breakdown summary")
    validation_errors: list[str] = Field(default_factory=list, description="Validation errors found")
    allocation_log: list[str] = Field(default_factory=list, description="Audit trail of allocation decisions")
    status: str = Field(..., description="success|partial|failed")
