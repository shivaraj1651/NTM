"""
Pydantic schemas for competitive intelligence agent.

Schemas for competitive intelligence data models including competitor
identification, channel metrics, and comprehensive CI reports.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CompetitorIdentity(BaseModel):
    """Competitive intelligence competitor identity schema."""
    name: str = Field(..., description="Competitor company name")
    confidence: int = Field(
        ...,
        ge=0,
        le=100,
        description="Confidence score for competitor identification (0-100)"
    )


class ChannelMetrics(BaseModel):
    """Metrics for a specific advertising channel."""
    model_config = ConfigDict(from_attributes=True)

    presence: bool = Field(..., description="Whether competitor has presence in this channel")
    estimated_monthly_spend: float | None = Field(
        None,
        ge=0,
        description="Estimated monthly ad spend in this channel (USD)"
    )
    estimated_monthly_impressions: int | None = Field(
        None,
        ge=0,
        description="Estimated monthly impressions in this channel"
    )
    placements: list[str] = Field(
        default_factory=list,
        description="Ad placements observed (e.g., search, display, feed)"
    )
    primary_keywords: list[str] = Field(
        default_factory=list,
        description="Primary keywords targeted in this channel"
    )
    primary_audiences: list[str] = Field(
        default_factory=list,
        description="Primary audience segments targeted"
    )


class CompetitorMetrics(BaseModel):
    """Comprehensive metrics for a single competitor."""
    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., description="Competitor company name")
    confidence_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Overall confidence score for this competitor's data (0-100)"
    )
    channels: dict[str, ChannelMetrics] = Field(
        default_factory=dict,
        description="Metrics per advertising channel (e.g., 'google_ads', 'meta')"
    )
    messaging_themes: list[str] = Field(
        default_factory=list,
        description="Primary messaging themes observed across campaigns"
    )
    geographic_focus: list[str] = Field(
        default_factory=list,
        description="Geographic regions/countries of focus"
    )
    estimated_annual_spend: float | None = Field(
        None,
        ge=0,
        description="Estimated total annual ad spend (USD)"
    )
    data_sources: list[str] = Field(
        default_factory=list,
        description="Data sources used (e.g., 'meta_ad_library', 'serpapi', 'manual_research')"
    )
    data_confidence: Literal["high", "medium", "low"] = Field(
        ...,
        description="Overall confidence level in the collected data"
    )


class CIReportInitial(BaseModel):
    """Initial competitive intelligence report with pending status."""
    model_config = ConfigDict(from_attributes=True)

    job_id: str = Field(..., description="Unique job ID for this CI analysis")
    mandate_id: str = Field(..., description="Associated mandate ID")
    competitors: list[CompetitorIdentity] = Field(
        default_factory=list,
        description="Initial list of identified competitors"
    )
    status: str = Field(
        default="pending",
        description="Report status (default: pending)"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when report was created (ISO format)"
    )


class WhitespaceOpportunities(BaseModel):
    """Identified whitespace opportunities in the competitive landscape."""
    model_config = ConfigDict(from_attributes=True)

    untapped_channels: list[str] = Field(
        default_factory=list,
        description="Advertising channels not being exploited by competitors"
    )
    messaging_gaps: list[str] = Field(
        default_factory=list,
        description="Messaging angles not covered by competitors"
    )
    geographic_gaps: list[str] = Field(
        default_factory=list,
        description="Geographic regions not being targeted by competitors"
    )


class CIReport(BaseModel):
    """Complete competitive intelligence report."""
    model_config = ConfigDict(from_attributes=True)

    mandate_id: str = Field(..., description="Associated mandate ID")
    job_id: str = Field(..., description="Unique job ID for this CI analysis")
    generated_at: datetime = Field(..., description="Timestamp when report was generated (ISO format)")
    tenant_id: str = Field(..., description="Tenant ID for multi-tenancy isolation")
    competitors: list[CompetitorMetrics] = Field(
        default_factory=list,
        description="Detailed metrics for each identified competitor"
    )
    whitespace_opportunities: WhitespaceOpportunities = Field(
        default_factory=WhitespaceOpportunities,
        description="Identified market whitespace opportunities"
    )
    market_concentration: str = Field(
        ...,
        description="Market concentration analysis (fragmented/concentrated/oligopoly)"
    )
    status: Literal["complete", "partial", "failed"] = Field(
        ...,
        description="Report completion status"
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when report was created (ISO format)"
    )
    updated_at: datetime = Field(
        ...,
        description="Timestamp when report was last updated (ISO format)"
    )
