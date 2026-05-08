"""Schemas module for NTM application."""

from backend.app.schemas.campaign_concept import (
    CampaignConcept,
    AudienceSegmentation,
    ChannelRecommendation,
    MessageArchitecture,
    CampaignPhasing,
    ToneBoard,
    RiskFlags,
)
from backend.app.schemas.media_plan import (
    Activation,
    BudgetSummary,
    PhaseBreakdown,
    ChannelSpend,
    ContingencyBreakdown,
    MediaPlanResponse,
    ChannelEnum,
    PhaseEnum,
    AudienceSegmentEnum,
)
from backend.app.schemas.budget_optimizer import (
    OptimizedActivation,
    ROIAnalysis,
    BudgetOptimizerResponse,
    OptimizationReport,
    PhaseROISummary,
    ChannelROISummary,
    BudgetShift,
    OptimizationActionEnum,
)

__all__ = [
    "CampaignConcept",
    "AudienceSegmentation",
    "ChannelRecommendation",
    "MessageArchitecture",
    "CampaignPhasing",
    "ToneBoard",
    "RiskFlags",
    "Activation",
    "BudgetSummary",
    "PhaseBreakdown",
    "ChannelSpend",
    "ContingencyBreakdown",
    "MediaPlanResponse",
    "ChannelEnum",
    "PhaseEnum",
    "AudienceSegmentEnum",
    "OptimizedActivation",
    "ROIAnalysis",
    "BudgetOptimizerResponse",
    "OptimizationReport",
    "PhaseROISummary",
    "ChannelROISummary",
    "BudgetShift",
    "OptimizationActionEnum",
]
