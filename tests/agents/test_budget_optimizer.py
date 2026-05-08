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
