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
