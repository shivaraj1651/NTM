"""Unit tests for Media Planner Agent (AGT-04)."""

import pytest
from datetime import date, timedelta
from backend.app.schemas.media_plan import ChannelEnum, PhaseEnum


class TestBudgetAllocator:
    """Tests for BudgetAllocator class."""

    def test_phase_allocation_40_40_20(self):
        """Budget should be allocated 40% Awareness, 40% Engagement, 20% Conversion."""
        from backend.app.agents.media_planner import BudgetAllocator

        allocator = BudgetAllocator()
        budget = 100000.0
        phases = allocator.allocate_by_phase(budget)

        assert phases["Awareness"] == 40000.0
        assert phases["Engagement"] == 40000.0
        assert phases["Conversion"] == 20000.0
        assert sum(phases.values()) == 100000.0

    def test_channel_weighting_equal_distribution(self):
        """Budget should be distributed equally across channels if no weights provided."""
        from backend.app.agents.media_planner import BudgetAllocator

        allocator = BudgetAllocator()
        phase_budget = 40000.0
        channels = [
            {"channel": "TikTok"},
            {"channel": "Instagram"},
            {"channel": "Email"}
        ]

        allocations = allocator.allocate_by_channel(phase_budget, channels)

        assert allocations["TikTok"] == pytest.approx(13333.33, abs=1)
        assert allocations["Instagram"] == pytest.approx(13333.33, abs=1)
        assert allocations["Email"] == pytest.approx(13333.34, abs=1)

    def test_channel_weighting_with_weights(self):
        """Budget should be distributed by channel weights (40%, 30%, 30%)."""
        from backend.app.agents.media_planner import BudgetAllocator

        allocator = BudgetAllocator()
        phase_budget = 40000.0
        channels = [
            {"channel": "TikTok", "weight": 0.4},
            {"channel": "Instagram", "weight": 0.3},
            {"channel": "Email", "weight": 0.3}
        ]

        allocations = allocator.allocate_by_channel(phase_budget, channels)

        assert allocations["TikTok"] == 16000.0
        assert allocations["Instagram"] == 12000.0
        assert allocations["Email"] == 12000.0

    def test_geography_equal_distribution(self):
        """Channel budget should be distributed equally across geographies."""
        from backend.app.agents.media_planner import BudgetAllocator

        allocator = BudgetAllocator()
        channel_budget = 16000.0
        geographies = ["US", "Canada"]

        allocations = allocator.allocate_by_geography(channel_budget, geographies)

        assert allocations["US"] == 8000.0
        assert allocations["Canada"] == 8000.0

    def test_contingency_reserve_10_pct(self):
        """Contingency should reserve 10% of total spend."""
        from backend.app.agents.media_planner import BudgetAllocator

        allocator = BudgetAllocator()
        total_spend = 90000.0

        contingency = allocator.calculate_contingency(total_spend, pct=0.10)

        assert contingency == 9000.0


class TestActivationGenerator:
    """Tests for ActivationGenerator class."""

    def test_reach_calculation_by_penetration(self):
        """Reach should be calculated as audience_size × penetration_pct."""
        from backend.app.agents.media_planner import ActivationGenerator

        generator = ActivationGenerator()
        audience_size = 10000
        penetration_pct = 0.25  # 25%

        reach = generator.calculate_reach(audience_size, penetration_pct)

        assert reach == 2500
        assert isinstance(reach, int)

    def test_cost_calculation_by_cpm(self):
        """Cost should be calculated as (reach / 1000) × CPM."""
        from backend.app.agents.media_planner import ActivationGenerator

        generator = ActivationGenerator()
        reach = 5000
        cpm = 10.0

        cost = generator.calculate_cost(reach, cpm)

        assert cost == pytest.approx(50.0)

    def test_frequency_by_phase(self):
        """Frequency should be deterministic per phase."""
        from backend.app.agents.media_planner import ActivationGenerator

        generator = ActivationGenerator()

        awareness_freq = generator.get_frequency_for_phase("Awareness")
        engagement_freq = generator.get_frequency_for_phase("Engagement")
        conversion_freq = generator.get_frequency_for_phase("Conversion")

        assert awareness_freq == "3x daily"
        assert engagement_freq == "2x daily"
        assert conversion_freq == "1x daily"

    def test_cpm_by_channel(self):
        """CPM rates should vary by channel."""
        from backend.app.agents.media_planner import ActivationGenerator

        generator = ActivationGenerator()

        tiktok_cpm = generator.get_cpm_for_channel("TikTok")
        tv_cpm = generator.get_cpm_for_channel("TV")
        email_cpm = generator.get_cpm_for_channel("Email")
        default_cpm = generator.get_cpm_for_channel("Unknown")

        # TikTok should be in range 3-8
        assert 3.0 <= tiktok_cpm <= 8.0
        # TV should be in range 15-30
        assert 15.0 <= tv_cpm <= 30.0
        # Email should be cheap
        assert email_cpm < 5.0
        # Default should be 10.0
        assert default_cpm == 10.0

    def test_penetration_by_phase(self):
        """Penetration rates should be deterministic per phase."""
        from backend.app.agents.media_planner import ActivationGenerator

        generator = ActivationGenerator()

        awareness_pen = generator.get_penetration_for_phase("Awareness")
        engagement_pen = generator.get_penetration_for_phase("Engagement")
        conversion_pen = generator.get_penetration_for_phase("Conversion")

        assert awareness_pen == 0.60  # 60%
        assert engagement_pen == 0.30  # 30%
        assert conversion_pen == 0.10  # 10%
