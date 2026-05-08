"""Unit tests for Media Planner Agent (AGT-04)."""

import pytest
from datetime import date, timedelta
import asyncio
from backend.app.schemas.media_plan import ChannelEnum, PhaseEnum, AudienceSegmentEnum


def get_valid_activation() -> dict:
    """
    Return a valid activation dictionary with all required fields.

    Used by TestActivationValidator to test schema validation.
    """
    return {
        "channel_enum": ChannelEnum.SOCIAL,
        "sub_channel": "TikTok",
        "format": "Video 15s",
        "geography": "US",
        "placement": "Feed",
        "phase": PhaseEnum.AWARENESS,
        "scheduled_date": date(2026, 6, 1),
        "duration": 14,
        "frequency": "3x daily",
        "audience_segment": AudienceSegmentEnum.PRIMARY,
        "estimated_reach": 500000,
        "estimated_cpm": 5.0,
        "cost_estimated": 2500.0,
        "message_version_ref": "TikTok (authentic, bold) - storytelling format"
    }


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


class TestOfflineConstraintHandler:
    """Tests for OfflineConstraintHandler class."""

    def test_tv_lead_time_4_weeks(self):
        """TV should have 28-day (4-week) lead time."""
        from backend.app.agents.media_planner import OfflineConstraintHandler

        handler = OfflineConstraintHandler()
        lead_time = handler.get_lead_time_days("TV")

        assert lead_time == 28

    def test_print_lead_time_2_weeks(self):
        """Print should have 14-day (2-week) lead time."""
        from backend.app.agents.media_planner import OfflineConstraintHandler

        handler = OfflineConstraintHandler()
        lead_time = handler.get_lead_time_days("Print")

        assert lead_time == 14

    def test_is_offline_channel_tv(self):
        """TV should be identified as offline channel."""
        from backend.app.agents.media_planner import OfflineConstraintHandler

        handler = OfflineConstraintHandler()
        is_offline = handler.is_offline("TV")

        assert is_offline is True

    def test_is_offline_channel_tiktok(self):
        """TikTok should not be identified as offline channel."""
        from backend.app.agents.media_planner import OfflineConstraintHandler

        handler = OfflineConstraintHandler()
        is_offline = handler.is_offline("TikTok")

        assert is_offline is False

    def test_scheduled_date_with_lead_time(self):
        """Scheduled date should be phase_start minus lead_time days."""
        from backend.app.agents.media_planner import OfflineConstraintHandler

        handler = OfflineConstraintHandler()
        phase_start = date(2026, 6, 1)
        scheduled_date = handler.calculate_scheduled_date("TV", phase_start)

        # TV has 28 days lead time, so 2026-06-01 - 28 days = 2026-05-04
        assert scheduled_date == date(2026, 5, 4)


class TestActivationValidator:
    """Tests for ActivationValidator class."""

    def test_validator_accepts_valid_activation(self):
        """Valid activation should return empty error list."""
        from backend.app.agents.media_planner import ActivationValidator

        validator = ActivationValidator()
        activation_dict = get_valid_activation()

        errors = validator.validate_schema(activation_dict)

        assert errors == []
        assert isinstance(errors, list)

    def test_validator_detects_missing_required_field(self):
        """Missing required field (cost_estimated) should be detected."""
        from backend.app.agents.media_planner import ActivationValidator

        validator = ActivationValidator()
        activation_dict = get_valid_activation()
        del activation_dict["cost_estimated"]  # Remove required field

        errors = validator.validate_schema(activation_dict)

        assert len(errors) > 0
        assert any("cost_estimated" in error for error in errors)

    def test_validator_detects_invalid_enum(self):
        """Invalid enum value (phase) should be detected."""
        from backend.app.agents.media_planner import ActivationValidator

        validator = ActivationValidator()
        activation_dict = get_valid_activation()
        activation_dict["phase"] = "InvalidPhase"  # Not a valid PhaseEnum value

        errors = validator.validate_schema(activation_dict)

        assert len(errors) > 0
        assert any("phase" in error for error in errors)

    def test_validator_detects_negative_cost(self):
        """Negative cost_estimated should be detected (must be >= 0)."""
        from backend.app.agents.media_planner import ActivationValidator

        validator = ActivationValidator()
        activation_dict = get_valid_activation()
        activation_dict["cost_estimated"] = -100.0  # Negative cost

        errors = validator.validate_schema(activation_dict)

        assert len(errors) > 0
        assert any("cost_estimated" in error for error in errors)

    def test_validator_detects_zero_reach(self):
        """Zero estimated_reach should be detected (must be >= 1)."""
        from backend.app.agents.media_planner import ActivationValidator

        validator = ActivationValidator()
        activation_dict = get_valid_activation()
        activation_dict["estimated_reach"] = 0  # Zero reach (must be >= 1)

        errors = validator.validate_schema(activation_dict)

        assert len(errors) > 0
        assert any("estimated_reach" in error for error in errors)


@pytest.mark.asyncio
async def test_media_planner_agent_generates_activations():
    """Integration test: media_planner_agent orchestrator generates full media plan."""
    from backend.app.agents.media_planner import media_planner_agent

    # Create mock campaign_concept with required channel_mix
    campaign_concept = {
        "campaign_name": "Test Campaign",
        "campaign_phasing": {
            "Awareness": {"start": date(2026, 6, 1), "end": date(2026, 6, 15)},
            "Engagement": {"start": date(2026, 6, 16), "end": date(2026, 6, 30)},
            "Conversion": {"start": date(2026, 7, 1), "end": date(2026, 7, 15)}
        },
        "channel_mix": [
            {"channel": "TikTok", "weight": 0.4},
            {"channel": "Instagram", "weight": 0.3},
            {"channel": "Email", "weight": 0.3}
        ],
        "tone_board": {"tone": "authentic, bold"},
        "message_architecture": {"primary": "storytelling format"}
    }

    # Create budget dict
    budget = {
        "total_budget": 100000.0,
        "currency": "USD",
        "contingency_pct": 0.10
    }

    # Create mandate_geography dict
    mandate_geography = {
        "regions": ["North America"],
        "markets": ["US", "Canada"],
        "countries": ["USA", "CAN"]
    }

    # Call the orchestrator
    result = await media_planner_agent(campaign_concept, budget, mandate_geography)

    # Assertions
    assert "activations" in result
    assert "budget_summary" in result
    assert isinstance(result["activations"], list)
    assert len(result["activations"]) > 0
    assert result["status"] in ["success", "partial", "failed"]
    assert "allocation_log" in result
    assert "validation_errors" in result
