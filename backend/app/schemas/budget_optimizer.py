"""Budget Optimizer output schemas."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import date
from enum import Enum


class OptimizationActionEnum(str, Enum):
    """Budget optimization action."""
    PRIORITIZED = "prioritized"
    REALLOCATED = "reallocated"
    DEPRIORITIZED = "deprioritized"
    UNCHANGED = "unchanged"


class OptimizedActivation(BaseModel):
    """Activation with optimization results."""
    id: str = Field(..., description="Activation ID from Media Planner")
    channel_enum: str = Field(..., description="Channel enum")
    sub_channel: str = Field(..., description="Sub-channel (e.g., TikTok)")
    format: str = Field(..., description="Media format")
    geography: str = Field(..., description="Geography")
    placement: str = Field(..., description="Placement")
    phase: str = Field(..., description="Campaign phase")
    scheduled_date: date = Field(..., description="Scheduled date (locked)")
    duration: int = Field(..., ge=1, description="Duration in days")
    frequency: str = Field(..., description="Delivery frequency")
    audience_segment: str = Field(..., description="Audience segment")
    estimated_reach: int = Field(..., ge=1, description="Estimated reach")
    estimated_cpm: float = Field(..., ge=0.01, description="CPM")
    original_cost_estimated: float = Field(..., ge=0, description="Original cost from Media Planner")
    optimized_cost_estimated: float = Field(..., ge=0, description="Optimized cost after reallocation")
    message_version_ref: str = Field(..., description="Message reference")
    lead_time_days: Optional[int] = Field(None, ge=0, description="Lead time (locked)")
    offline_constraints: Optional[str] = Field(None, description="Offline constraints (locked)")
    estimated_conversion_rate: float = Field(..., ge=0.0, le=1.0, description="Estimated conversion rate")
    reach_weighted_conversions: int = Field(..., ge=0, description="reach × conversion_rate")
    roi_per_dollar: float = Field(..., ge=0, description="reach_weighted_conversions / cost")
    optimization_action: OptimizationActionEnum = Field(..., description="Type of optimization action")
    reason: str = Field(..., description="Reason for optimization decision")


class PhaseROISummary(BaseModel):
    """ROI summary for a single phase."""
    allocated_budget: float = Field(..., ge=0, description="Phase budget")
    total_reach: int = Field(..., ge=0, description="Total reach in phase")
    total_reach_weighted_conversions: int = Field(..., ge=0, description="Total reach-weighted conversions")
    average_roi: float = Field(..., ge=0, description="Average ROI per dollar")
    channel_breakdown: Dict[str, float] = Field(..., description="Budget per channel in phase")


class ChannelROISummary(BaseModel):
    """ROI summary for a single channel."""
    total_allocated_budget: float = Field(..., ge=0, description="Total budget across phases")
    activation_count: int = Field(..., ge=0, description="Number of activations")
    total_reach: int = Field(..., ge=0, description="Total reach")
    total_reach_weighted_conversions: int = Field(..., ge=0, description="Total reach-weighted conversions")
    average_roi: float = Field(..., ge=0, description="Average ROI per dollar")


class ROIAnalysis(BaseModel):
    """Complete ROI analysis."""
    phase_summary: Dict[str, PhaseROISummary] = Field(..., description="Summary by phase")
    channel_summary: Dict[str, ChannelROISummary] = Field(..., description="Summary by channel")
    total_budget: float = Field(..., ge=0, description="Total campaign budget")
    total_reach: int = Field(..., ge=0, description="Total reach across all activations")
    total_reach_weighted_conversions: int = Field(..., ge=0, description="Total reach-weighted conversions")
    campaign_roi: float = Field(..., ge=0, description="Overall campaign ROI")


class BudgetShift(BaseModel):
    """Individual budget reallocation."""
    from_activation_id: str = Field(..., description="Source activation ID")
    from_activation_name: str = Field(..., description="Source activation name")
    to_activation_id: str = Field(..., description="Destination activation ID")
    to_activation_name: str = Field(..., description="Destination activation name")
    amount: float = Field(..., gt=0, description="Amount reallocated")
    reason: str = Field(..., description="Reason for shift")


class PrioritizedActivation(BaseModel):
    """Activation that was prioritized in optimization."""
    activation_id: str = Field(..., description="Activation ID")
    activation_name: str = Field(..., description="Activation display name")
    original_budget: float = Field(..., ge=0, description="Original budget")
    optimized_budget: float = Field(..., ge=0, description="Optimized budget")
    budget_increase_pct: float = Field(..., description="Percentage increase")
    roi_per_dollar: float = Field(..., ge=0, description="ROI metric")
    reason: str = Field(..., description="Why this activation was prioritized")


class DeprioritizedActivation(BaseModel):
    """Activation that was deprioritized in optimization."""
    activation_id: str = Field(..., description="Activation ID")
    activation_name: str = Field(..., description="Activation display name")
    original_budget: float = Field(..., ge=0, description="Original budget")
    optimized_budget: float = Field(..., ge=0, description="Optimized budget (reduced)")
    budget_decrease_pct: float = Field(..., description="Percentage decrease")
    roi_per_dollar: float = Field(..., ge=0, description="ROI metric")
    reason: str = Field(..., description="Why this activation was deprioritized")


class ConstraintsValidation(BaseModel):
    """Validation of constraint maintenance."""
    phase_budgets: str = Field(..., description="Phase budget status")
    scheduled_dates: str = Field(..., description="Scheduled date status")
    channels: str = Field(..., description="Channel preservation status")
    geographies: str = Field(..., description="Geography preservation status")


class OptimizationReport(BaseModel):
    """Detailed optimization report."""
    summary: str = Field(..., description="One-line summary of optimization")
    budget_shifts: List[BudgetShift] = Field(default_factory=list, description="All budget reallocations")
    prioritized_activations: List[PrioritizedActivation] = Field(default_factory=list, description="Prioritized activations")
    deprioritized_activations: List[DeprioritizedActivation] = Field(default_factory=list, description="Deprioritized activations")
    constraints_maintained: ConstraintsValidation = Field(..., description="Verification of constraints")


class BudgetOptimizerResponse(BaseModel):
    """Complete Budget Optimizer response."""
    optimized_activations: List[OptimizedActivation] = Field(..., description="Optimized activation list")
    roi_analysis: ROIAnalysis = Field(..., description="ROI analysis and metrics")
    optimization_report: OptimizationReport = Field(..., description="Detailed optimization report")
    validation_errors: List[str] = Field(default_factory=list, description="Validation errors")
    status: str = Field(..., description="success|partial|failed")
