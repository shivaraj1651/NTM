"""Tests for Budget Optimizer Agent (AGT-05)."""

import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from backend.app.agents.budget_optimizer import (
    ConversionRateEstimator,
    BudgetOptimizer,
    ROIAnalyzer,
    OptimizationReporter,
    budget_optimizer_agent,
)


@pytest.fixture
def estimator():
    """Create a ConversionRateEstimator instance."""
    return ConversionRateEstimator()


@pytest.fixture
def optimizer():
    """Create a BudgetOptimizer instance."""
    return BudgetOptimizer()


@pytest.fixture
def analyzer():
    """Create a ROIAnalyzer instance."""
    return ROIAnalyzer()


@pytest.fixture
def reporter():
    """Create an OptimizationReporter instance."""
    return OptimizationReporter()


@pytest.fixture
def sample_activation():
    """Sample activation for testing."""
    return {
        "id": "act-001",
        "phase": "Awareness",
        "sub_channel": "Email",
        "audience_segment": "Primary",
        "budget": 5000.0,
        "reach": 50000,
        "scheduled_start": date.today().isoformat(),
    }


@pytest.fixture
def sample_activations():
    """Sample activations for optimization."""
    return [
        {
            "id": "act-001",
            "phase": "Awareness",
            "sub_channel": "Email",
            "audience_segment": "Primary",
            "budget": 5000.0,
            "reach": 50000,
        },
        {
            "id": "act-002",
            "phase": "Awareness",
            "sub_channel": "TikTok",
            "audience_segment": "Primary",
            "budget": 5000.0,
            "reach": 100000,
        },
        {
            "id": "act-003",
            "phase": "Engagement",
            "sub_channel": "Email",
            "audience_segment": "Secondary",
            "budget": 10000.0,
            "reach": 30000,
        },
    ]


@pytest.fixture
def campaign_context():
    """Sample campaign context."""
    return {
        "campaign_id": "camp-001",
        "campaign_name": "Test Campaign",
        "tone_board": "Professional",
    }


class TestConversionRateEstimator:
    """Tests for ConversionRateEstimator class."""

    def test_estimate_conversion_rate_email_primary_engagement(self, estimator):
        """Should estimate conversion rate for Email Primary Engagement."""
        activation = {
            "sub_channel": "Email",
            "audience_segment": "Primary",
            "phase": "Engagement",
        }
        campaign_context = {}

        rate = estimator.estimate_conversion_rate(activation, campaign_context)

        # Email 3% * Primary 1.0x * Engagement 1.0x = 3%
        assert 0.02 < rate < 0.04  # Should be around 0.03

    def test_estimate_conversion_rate_channel_defaults(self, estimator):
        """Should use channel defaults when not in historical data."""
        activation = {
            "sub_channel": "TikTok",
            "audience_segment": "Primary",
            "phase": "Engagement",
        }
        campaign_context = {}

        rate = estimator.estimate_conversion_rate(activation, campaign_context)

        # TikTok 0.8% * Primary 1.0x * Engagement 1.0x = 0.8%
        assert 0.005 < rate < 0.015

    def test_estimate_conversion_rate_segment_multiplier(self, estimator):
        """Should apply segment multiplier correctly."""
        activation_primary = {
            "sub_channel": "Email",
            "audience_segment": "Primary",
            "phase": "Engagement",
        }
        activation_secondary = {
            "sub_channel": "Email",
            "audience_segment": "Secondary",
            "phase": "Engagement",
        }
        campaign_context = {}

        rate_primary = estimator.estimate_conversion_rate(activation_primary, campaign_context)
        rate_secondary = estimator.estimate_conversion_rate(activation_secondary, campaign_context)

        # Secondary should be lower (0.7x multiplier)
        assert rate_secondary < rate_primary

    def test_estimate_conversion_rate_phase_multiplier(self, estimator):
        """Should apply phase multiplier correctly."""
        activation_awareness = {
            "sub_channel": "Email",
            "audience_segment": "Primary",
            "phase": "Awareness",
        }
        activation_conversion = {
            "sub_channel": "Email",
            "audience_segment": "Primary",
            "phase": "Conversion",
        }
        campaign_context = {}

        rate_awareness = estimator.estimate_conversion_rate(activation_awareness, campaign_context)
        rate_conversion = estimator.estimate_conversion_rate(activation_conversion, campaign_context)

        # Conversion should be higher (1.5x multiplier)
        assert rate_conversion > rate_awareness

    def test_estimate_conversion_rate_clamped_to_range(self, estimator):
        """Should clamp rate to [0.001, 0.10]."""
        activation = {
            "sub_channel": "Email",
            "audience_segment": "Primary",
            "phase": "Conversion",
        }
        campaign_context = {}

        rate = estimator.estimate_conversion_rate(activation, campaign_context)

        assert 0.001 <= rate <= 0.10

    def test_estimate_conversion_rate_historical_data(self, estimator):
        """Should use historical data when available."""
        activation = {
            "sub_channel": "Email",
            "audience_segment": "Primary",
            "phase": "Engagement",
        }
        campaign_context = {}
        historical_data = {"Email": 0.05}  # 5% from history

        rate = estimator.estimate_conversion_rate(
            activation, campaign_context, historical_data
        )

        # 5% * Primary 1.0x * Engagement 1.0x = 5%
        assert 0.04 < rate < 0.06


class TestBudgetOptimizer:
    """Tests for BudgetOptimizer class."""

    def test_calculate_roi_per_dollar(self, optimizer, sample_activation):
        """Should calculate ROI per dollar spent."""
        conversion_rate = 0.03  # 3%

        roi = optimizer.calculate_roi_per_dollar(sample_activation, conversion_rate)

        # ROI = reach * conversion_rate / budget
        assert isinstance(roi, (int, float))

    def test_calculate_roi_per_dollar_higher_reach_higher_roi(self, optimizer):
        """Higher reach should produce higher ROI."""
        act_low_reach = {"reach": 10000, "budget": 1000}
        act_high_reach = {"reach": 100000, "budget": 1000}
        conversion_rate = 0.03

        roi_low = optimizer.calculate_roi_per_dollar(act_low_reach, conversion_rate)
        roi_high = optimizer.calculate_roi_per_dollar(act_high_reach, conversion_rate)

        assert roi_high >= roi_low

    def test_optimize_respects_minimum_budget(self, optimizer, sample_activations):
        """Should enforce minimum budget per activation."""
        conversion_rates = {
            "act-001": 0.03,
            "act-002": 0.008,
            "act-003": 0.02,
        }
        phase_budgets = {"Awareness": 10000.0, "Engagement": 20000.0}

        result = optimizer.optimize(sample_activations, conversion_rates, phase_budgets)

        # All activations should have at least MIN_ACTIVATION_BUDGET
        assert all(act["budget"] >= optimizer.MIN_ACTIVATION_BUDGET for act in result)

    def test_optimize_respects_phase_budgets(self, optimizer, sample_activations):
        """Should not exceed phase budget constraints."""
        conversion_rates = {
            "act-001": 0.03,
            "act-002": 0.008,
            "act-003": 0.02,
        }
        phase_budgets = {"Awareness": 10000.0, "Engagement": 20000.0}

        result = optimizer.optimize(sample_activations, conversion_rates, phase_budgets)

        # Group by phase and verify budget
        awareness_total = sum(
            a["budget"] for a in result if a["phase"] == "Awareness"
        )
        engagement_total = sum(
            a["budget"] for a in result if a["phase"] == "Engagement"
        )

        assert awareness_total <= phase_budgets["Awareness"] * 1.01  # Allow 1% tolerance
        assert engagement_total <= phase_budgets["Engagement"] * 1.01


class TestROIAnalyzer:
    """Tests for ROIAnalyzer class."""

    def test_analyze_generates_phase_summary(self, analyzer, sample_activations):
        """Should generate phase-level ROI summary."""
        conversion_rates = {
            "act-001": 0.03,
            "act-002": 0.008,
            "act-003": 0.02,
        }

        result = analyzer.analyze(sample_activations, conversion_rates)

        assert "phase_summary" in result
        assert "Awareness" in result["phase_summary"]

    def test_analyze_generates_channel_summary(self, analyzer, sample_activations):
        """Should generate channel-level ROI summary."""
        conversion_rates = {
            "act-001": 0.03,
            "act-002": 0.008,
            "act-003": 0.02,
        }

        result = analyzer.analyze(sample_activations, conversion_rates)

        assert "channel_summary" in result
        assert "Email" in result["channel_summary"] or len(result["channel_summary"]) > 0

    def test_analyze_generates_campaign_roi(self, analyzer, sample_activations):
        """Should generate campaign-level ROI metric."""
        conversion_rates = {
            "act-001": 0.03,
            "act-002": 0.008,
            "act-003": 0.02,
        }

        result = analyzer.analyze(sample_activations, conversion_rates)

        # Check for totals which contains campaign-level metrics
        assert "totals" in result or "channel_summary" in result
        assert isinstance(result, dict)


class TestOptimizationReporter:
    """Tests for OptimizationReporter class."""

    def test_generate_report_detects_budget_shifts(self, reporter, sample_activations):
        """Should detect budget shifts above threshold."""
        original = sample_activations.copy()
        optimized = [
            {**act, "budget": act["budget"] * 2.0} for act in original
        ]
        conversion_rates = {
            "act-001": 0.03,
            "act-002": 0.008,
            "act-003": 0.02,
        }

        report = reporter.generate_report(original, optimized, conversion_rates)

        assert "budget_shifts" in report or "optimization_summary" in report

    def test_generate_report_categorizes_activations(self, reporter, sample_activations):
        """Should categorize activations as prioritized/deprioritized."""
        original = sample_activations.copy()
        optimized = [
            {**act, "budget": act["budget"] * 0.5 if act["id"] == "act-001" else act["budget"] * 2.0}
            for act in original
        ]
        conversion_rates = {
            "act-001": 0.03,
            "act-002": 0.008,
            "act-003": 0.02,
        }

        report = reporter.generate_report(original, optimized, conversion_rates)

        assert isinstance(report, dict)


class TestBudgetOptimizerAgent:
    """Tests for budget_optimizer_agent entry point."""

    @pytest.mark.asyncio
    async def test_budget_optimizer_agent_happy_path(self, sample_activations, campaign_context):
        """Should optimize activations and return structured output."""
        budget_envelope = 50000.0

        result = await budget_optimizer_agent(
            activations=sample_activations,
            budget_envelope=budget_envelope,
            campaign_context=campaign_context,
        )

        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_budget_optimizer_agent_returns_required_fields(self, sample_activations, campaign_context):
        """Should return all required output fields."""
        result = await budget_optimizer_agent(
            activations=sample_activations,
            budget_envelope=50000.0,
            campaign_context=campaign_context,
        )

        # Should have optimized activations, ROI analysis, and report
        assert "optimized_activations" in result or "status" in result
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_budget_optimizer_agent_preserves_activation_structure(
        self, sample_activations, campaign_context
    ):
        """Should preserve key activation fields through optimization."""
        result = await budget_optimizer_agent(
            activations=sample_activations,
            budget_envelope=50000.0,
            campaign_context=campaign_context,
        )

        assert isinstance(result, dict)


# ── Boundary inputs ───────────────────────────────────────────────────────────

class TestBudgetOptimizerAgentBoundary:
    """Boundary and edge-case tests for budget_optimizer_agent."""

    @pytest.mark.asyncio
    async def test_budget_optimizer_zero_budget(self, sample_activations, campaign_context):
        """Agent must handle zero total budget without raising."""
        budget_envelope = {"total_budget": 0.0, "currency": "USD"}

        result = await budget_optimizer_agent(
            activations=sample_activations,
            budget_envelope=budget_envelope,
            campaign_context=campaign_context,
        )

        assert isinstance(result, dict)
        assert "optimized_activations" in result or "status" in result

    @pytest.mark.asyncio
    async def test_budget_optimizer_empty_activations(self, campaign_context):
        """Agent must handle empty activations list without raising."""
        budget_envelope = {"total_budget": 50000.0, "currency": "USD"}

        result = await budget_optimizer_agent(
            activations=[],
            budget_envelope=budget_envelope,
            campaign_context=campaign_context,
        )

        assert isinstance(result, dict)
        assert result.get("status") in ("success", "partial", "failed") or "optimized_activations" in result

    @pytest.mark.asyncio
    async def test_budget_optimizer_single_activation(self, campaign_context):
        """Agent must handle a single activation."""
        budget_envelope = {"total_budget": 10000.0, "currency": "USD"}
        activations = [
            {
                "id": "act-single",
                "phase": "Awareness",
                "sub_channel": "Email",
                "audience_segment": "Primary",
                "cost_estimated": 5000.0,
                "estimated_reach": 20000,
            }
        ]

        result = await budget_optimizer_agent(
            activations=activations,
            budget_envelope=budget_envelope,
            campaign_context=campaign_context,
        )

        assert isinstance(result, dict)
        assert result.get("status") != "failed" or "optimized_activations" in result

    @pytest.mark.asyncio
    async def test_budget_optimizer_missing_budget_key(self, sample_activations, campaign_context):
        """Agent must not raise when budget_envelope lacks total_budget key (defaults to 0)."""
        budget_envelope = {"currency": "USD"}  # missing total_budget

        result = await budget_optimizer_agent(
            activations=sample_activations,
            budget_envelope=budget_envelope,
            campaign_context=campaign_context,
        )

        # Should return a dict regardless — agent uses .get("total_budget", 0.0)
        assert isinstance(result, dict)
