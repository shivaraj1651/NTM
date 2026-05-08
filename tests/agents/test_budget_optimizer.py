"""Unit tests for Budget Optimizer Agent (AGT-05)."""

import pytest
from datetime import date


class TestConversionRateEstimator:
    """Tests for ConversionRateEstimator class."""

    def test_estimate_rate_returns_float_between_0_and_1(self):
        """Estimated conversion rate should be 0.001 to 0.10 (clamped)."""
        from backend.app.agents.budget_optimizer import ConversionRateEstimator

        estimator = ConversionRateEstimator()

        # Test various activations
        activation = {
            "sub_channel": "TikTok",
            "audience_segment": "Primary",
            "phase": "Awareness"
        }
        campaign_context = {
            "tone_board": {"adjectives": ["authentic", "bold"]}
        }

        rate = estimator.estimate_conversion_rate(activation, campaign_context)

        assert isinstance(rate, float)
        assert 0.001 <= rate <= 0.10

    def test_estimate_rate_channel_defaults(self):
        """Should use channel defaults if no historical data."""
        from backend.app.agents.budget_optimizer import ConversionRateEstimator

        estimator = ConversionRateEstimator()

        # Email has high base rate
        email_rate = estimator.estimate_conversion_rate(
            {"sub_channel": "Email", "audience_segment": "Primary", "phase": "Conversion"},
            {}
        )

        # Social has lower rate
        social_rate = estimator.estimate_conversion_rate(
            {"sub_channel": "TikTok", "audience_segment": "Primary", "phase": "Conversion"},
            {}
        )

        assert email_rate > social_rate

    def test_estimate_rate_segment_multiplier(self):
        """Segment should affect conversion rate (Primary > Secondary > Tertiary)."""
        from backend.app.agents.budget_optimizer import ConversionRateEstimator

        estimator = ConversionRateEstimator()

        primary_rate = estimator.estimate_conversion_rate(
            {"sub_channel": "Email", "audience_segment": "Primary", "phase": "Conversion"},
            {}
        )

        secondary_rate = estimator.estimate_conversion_rate(
            {"sub_channel": "Email", "audience_segment": "Secondary", "phase": "Conversion"},
            {}
        )

        assert primary_rate > secondary_rate

    def test_estimate_rate_phase_multiplier(self):
        """Phase should affect conversion rate (Conversion > Engagement > Awareness)."""
        from backend.app.agents.budget_optimizer import ConversionRateEstimator

        estimator = ConversionRateEstimator()

        awareness_rate = estimator.estimate_conversion_rate(
            {"sub_channel": "Email", "audience_segment": "Primary", "phase": "Awareness"},
            {}
        )

        conversion_rate = estimator.estimate_conversion_rate(
            {"sub_channel": "Email", "audience_segment": "Primary", "phase": "Conversion"},
            {}
        )

        assert conversion_rate > awareness_rate

    def test_estimate_rate_clamped_to_valid_range(self):
        """Rate must be clamped to 0.001-0.10 range."""
        from backend.app.agents.budget_optimizer import ConversionRateEstimator

        estimator = ConversionRateEstimator()

        rate = estimator.estimate_conversion_rate(
            {"sub_channel": "TikTok", "audience_segment": "Primary", "phase": "Awareness"},
            {}
        )

        assert 0.001 <= rate <= 0.10


class TestBudgetOptimizer:
    """Tests for BudgetOptimizer class."""

    def test_calculate_roi_per_dollar(self):
        """ROI should be reach-weighted-conversions / cost."""
        from backend.app.agents.budget_optimizer import BudgetOptimizer

        optimizer = BudgetOptimizer()

        activation = {
            "estimated_reach": 500000,
            "optimized_cost_estimated": 2500.0,
        }
        conversion_rate = 0.008

        roi = optimizer.calculate_roi_per_dollar(activation, conversion_rate)

        # (500000 × 0.008) / 2500 = 4000 / 2500 = 1.6
        assert roi == pytest.approx(1.6, abs=0.01)

    def test_optimize_respects_phase_budget_total(self):
        """Total phase budget must equal original allocation."""
        from backend.app.agents.budget_optimizer import BudgetOptimizer

        optimizer = BudgetOptimizer()

        activations = [
            {
                "id": "a1",
                "phase": "Awareness",
                "optimized_cost_estimated": 10000.0,
                "estimated_reach": 500000,
            },
            {
                "id": "a2",
                "phase": "Awareness",
                "optimized_cost_estimated": 10000.0,
                "estimated_reach": 400000,
            },
        ]

        conversion_rates = {"a1": 0.008, "a2": 0.006}
        phase_budgets = {"Awareness": 40000.0, "Engagement": 40000.0, "Conversion": 20000.0}

        optimized = optimizer.optimize(activations, conversion_rates, phase_budgets)

        awareness_total = sum(a["optimized_cost_estimated"] for a in optimized if a["phase"] == "Awareness")
        assert awareness_total == pytest.approx(40000.0, abs=1.0)

    def test_optimize_prioritizes_high_roi(self):
        """High-ROI activations should get more budget."""
        from backend.app.agents.budget_optimizer import BudgetOptimizer

        optimizer = BudgetOptimizer()

        activations = [
            {
                "id": "high_roi",
                "phase": "Conversion",
                "optimized_cost_estimated": 5000.0,
                "estimated_reach": 100000,
            },
            {
                "id": "low_roi",
                "phase": "Conversion",
                "optimized_cost_estimated": 5000.0,
                "estimated_reach": 50000,
            },
        ]

        conversion_rates = {"high_roi": 0.030, "low_roi": 0.010}
        phase_budgets = {"Awareness": 40000.0, "Engagement": 40000.0, "Conversion": 20000.0}

        optimized = optimizer.optimize(activations, conversion_rates, phase_budgets)

        high_roi_activation = next(a for a in optimized if a["id"] == "high_roi")
        low_roi_activation = next(a for a in optimized if a["id"] == "low_roi")

        assert high_roi_activation["optimized_cost_estimated"] > low_roi_activation["optimized_cost_estimated"]

    def test_optimize_minimum_activation_budget(self):
        """Activations should not drop below $100."""
        from backend.app.agents.budget_optimizer import BudgetOptimizer

        optimizer = BudgetOptimizer()

        activations = [
            {
                "id": "low_roi",
                "phase": "Awareness",
                "optimized_cost_estimated": 20000.0,
                "estimated_reach": 10000,
            },
        ]

        conversion_rates = {"low_roi": 0.001}
        phase_budgets = {"Awareness": 40000.0, "Engagement": 40000.0, "Conversion": 20000.0}

        optimized = optimizer.optimize(activations, conversion_rates, phase_budgets)

        assert all(a["optimized_cost_estimated"] >= 100.0 for a in optimized)


class TestROIAnalyzer:
    """Tests for ROIAnalyzer class."""

    def test_analyze_roi_phase_summary(self):
        """Should generate phase ROI breakdown with channel breakdown."""
        from backend.app.agents.budget_optimizer import ROIAnalyzer

        analyzer = ROIAnalyzer()

        optimized_activations = [
            {
                "id": "a1",
                "phase": "Awareness",
                "sub_channel": "TikTok",
                "estimated_reach": 500000,
                "optimized_cost_estimated": 5000.0,
            },
            {
                "id": "a2",
                "phase": "Awareness",
                "sub_channel": "Instagram",
                "estimated_reach": 300000,
                "optimized_cost_estimated": 3000.0,
            },
            {
                "id": "a3",
                "phase": "Conversion",
                "sub_channel": "Email",
                "estimated_reach": 100000,
                "optimized_cost_estimated": 1000.0,
            },
        ]

        conversion_rates = {
            "a1": 0.008,
            "a2": 0.006,
            "a3": 0.030,
        }

        result = analyzer.analyze(optimized_activations, conversion_rates)

        # Check structure
        assert "phase_summary" in result
        assert "Awareness" in result["phase_summary"]
        assert "Conversion" in result["phase_summary"]

        # Awareness phase: (500000*0.008 + 300000*0.006) / (5000+3000) = 5800/8000 = 0.725
        assert result["phase_summary"]["Awareness"]["roi"] == pytest.approx(0.725, abs=0.01)

        # Conversion phase: (100000*0.030) / 1000 = 3000/1000 = 3.0
        assert result["phase_summary"]["Conversion"]["roi"] == pytest.approx(3.0, abs=0.01)

        # Check channel breakdown in Awareness phase
        assert "channel_breakdown" in result["phase_summary"]["Awareness"]
        awareness_channels = result["phase_summary"]["Awareness"]["channel_breakdown"]
        assert "TikTok" in awareness_channels
        assert "Instagram" in awareness_channels

    def test_analyze_roi_channel_summary(self):
        """Should generate channel ROI breakdown across all phases."""
        from backend.app.agents.budget_optimizer import ROIAnalyzer

        analyzer = ROIAnalyzer()

        optimized_activations = [
            {
                "id": "a1",
                "phase": "Awareness",
                "sub_channel": "Email",
                "estimated_reach": 50000,
                "optimized_cost_estimated": 1000.0,
            },
            {
                "id": "a2",
                "phase": "Conversion",
                "sub_channel": "Email",
                "estimated_reach": 20000,
                "optimized_cost_estimated": 500.0,
            },
        ]

        conversion_rates = {
            "a1": 0.030,
            "a2": 0.030,
        }

        result = analyzer.analyze(optimized_activations, conversion_rates)

        # Check structure
        assert "channel_summary" in result
        assert "Email" in result["channel_summary"]

        # Email total: (50000*0.030 + 20000*0.030) / (1000+500) = 2100/1500 = 1.4
        assert result["channel_summary"]["Email"]["roi"] == pytest.approx(1.4, abs=0.01)

    def test_analyze_roi_total_campaign(self):
        """Should calculate total campaign ROI across all activations."""
        from backend.app.agents.budget_optimizer import ROIAnalyzer

        analyzer = ROIAnalyzer()

        optimized_activations = [
            {
                "id": "a1",
                "phase": "Awareness",
                "sub_channel": "TikTok",
                "estimated_reach": 1000000,
                "optimized_cost_estimated": 10000.0,
            },
            {
                "id": "a2",
                "phase": "Conversion",
                "sub_channel": "Email",
                "estimated_reach": 50000,
                "optimized_cost_estimated": 5000.0,
            },
        ]

        conversion_rates = {
            "a1": 0.008,
            "a2": 0.030,
        }

        result = analyzer.analyze(optimized_activations, conversion_rates)

        # Check structure
        assert "totals" in result

        # Campaign total: (1000000*0.008 + 50000*0.030) / (10000+5000)
        # = (8000 + 1500) / 15000 = 9500 / 15000 = 0.633...
        assert result["totals"]["roi"] == pytest.approx(0.633, abs=0.01)
        assert result["totals"]["total_reach_weighted_conversions"] == 9500
        assert result["totals"]["total_budget"] == pytest.approx(15000.0, abs=1.0)


class TestOptimizationReporter:
    """Tests for OptimizationReporter class."""

    def test_report_identifies_budget_shifts(self):
        """Should detect activations with budget changes."""
        from backend.app.agents.budget_optimizer import OptimizationReporter

        reporter = OptimizationReporter()

        original = [
            {"id": "a1", "sub_channel": "TikTok", "phase": "Awareness", "optimized_cost_estimated": 5000.0},
            {"id": "a2", "sub_channel": "Instagram", "phase": "Awareness", "optimized_cost_estimated": 5000.0},
        ]

        optimized = [
            {"id": "a1", "sub_channel": "TikTok", "phase": "Awareness", "optimized_cost_estimated": 6000.0},
            {"id": "a2", "sub_channel": "Instagram", "phase": "Awareness", "optimized_cost_estimated": 4000.0},
        ]

        conversion_rates = {"a1": 0.008, "a2": 0.006}

        report = reporter.generate_report(original, optimized, conversion_rates)

        assert len(report["budget_shifts"]) > 0

    def test_report_categorizes_prioritized(self):
        """Should identify prioritized activations (budget increase)."""
        from backend.app.agents.budget_optimizer import OptimizationReporter

        reporter = OptimizationReporter()

        original = [
            {"id": "a1", "sub_channel": "TikTok", "phase": "Awareness", "optimized_cost_estimated": 3000.0},
        ]

        optimized = [
            {"id": "a1", "sub_channel": "TikTok", "phase": "Awareness", "optimized_cost_estimated": 5000.0},
        ]

        conversion_rates = {"a1": 0.008}

        report = reporter.generate_report(original, optimized, conversion_rates)

        assert len(report["prioritized_activations"]) > 0

    def test_report_categorizes_deprioritized(self):
        """Should identify deprioritized activations (budget decrease)."""
        from backend.app.agents.budget_optimizer import OptimizationReporter

        reporter = OptimizationReporter()

        original = [
            {"id": "a1", "sub_channel": "Display", "phase": "Awareness", "optimized_cost_estimated": 5000.0},
        ]

        optimized = [
            {"id": "a1", "sub_channel": "Display", "phase": "Awareness", "optimized_cost_estimated": 2000.0},
        ]

        conversion_rates = {"a1": 0.002}

        report = reporter.generate_report(original, optimized, conversion_rates)

        assert len(report["deprioritized_activations"]) > 0


@pytest.mark.asyncio
async def test_budget_optimizer_agent_generates_optimized_plan():
    """Orchestrator should generate optimized activation plan."""
    from backend.app.agents.budget_optimizer import budget_optimizer_agent

    # Mock Media Planner output
    activations = [
        {
            "id": "a1",
            "channel_enum": "Social",
            "sub_channel": "TikTok",
            "format": "Video 15s",
            "geography": "US",
            "placement": "Feed",
            "phase": "Awareness",
            "scheduled_date": date(2026, 6, 1),
            "duration": 14,
            "frequency": "3x daily",
            "audience_segment": "Primary",
            "estimated_reach": 500000,
            "estimated_cpm": 5.0,
            "cost_estimated": 2500.0,
            "message_version_ref": "TikTok message",
            "lead_time_days": 0,
            "offline_constraints": None,
        },
        {
            "id": "a2",
            "channel_enum": "Email",
            "sub_channel": "Email",
            "format": "Newsletter",
            "geography": "US",
            "placement": "Inbox",
            "phase": "Conversion",
            "scheduled_date": date(2026, 7, 15),
            "duration": 7,
            "frequency": "1x daily",
            "audience_segment": "Primary",
            "estimated_reach": 100000,
            "estimated_cpm": 0.5,
            "cost_estimated": 500.0,
            "message_version_ref": "Email message",
            "lead_time_days": 0,
            "offline_constraints": None,
        },
    ]

    budget_envelope = {
        "total_budget": 100000.0,
        "currency": "USD",
    }

    campaign_context = {
        "name": "Q2 Campaign",
        "tone_board": {"adjectives": ["authentic", "bold"]},
        "target_audience": "18-35",
    }

    result = await budget_optimizer_agent(activations, budget_envelope, campaign_context)

    assert "optimized_activations" in result
    assert "roi_analysis" in result
    assert "optimization_report" in result
    assert len(result["optimized_activations"]) > 0
    assert result["status"] in ["success", "partial", "failed"]
