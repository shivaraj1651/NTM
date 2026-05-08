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
