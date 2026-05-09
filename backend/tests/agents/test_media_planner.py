"""Tests for Media Planner Agent (AGT-04)."""

import pytest
from datetime import date, timedelta
from backend.app.agents.media_planner import (
    BudgetAllocator,
    ActivationGenerator,
    OfflineConstraintHandler,
    ActivationValidator,
    media_planner_agent,
)
from backend.app.schemas.media_plan import (
    Activation,
    PhaseEnum,
    ChannelEnum,
    AudienceSegmentEnum,
)


@pytest.fixture
def budget_allocator():
    """Create a BudgetAllocator instance."""
    return BudgetAllocator()


@pytest.fixture
def activation_generator():
    """Create an ActivationGenerator instance."""
    return ActivationGenerator()


@pytest.fixture
def constraint_handler():
    """Create an OfflineConstraintHandler instance."""
    return OfflineConstraintHandler()


@pytest.fixture
def validator():
    """Create an ActivationValidator instance."""
    return ActivationValidator()


@pytest.fixture
def sample_activation():
    """Sample activation for testing."""
    return {
        "id": "act-001",
        "phase": "Awareness",
        "channel": "TikTok",
        "sub_channel": "TikTok",
        "geography": "US",
        "audience_segment": "Primary",
        "budget": 10000.0,
        "scheduled_start": date.today().isoformat(),
        "scheduled_end": (date.today() + timedelta(days=30)).isoformat(),
    }


@pytest.fixture
def sample_campaign_context():
    """Sample campaign context."""
    return {
        "campaign_id": "camp-001",
        "campaign_name": "Summer 2026",
        "budget_envelope": 100000.0,
        "phases": {
            "Awareness": 40000.0,
            "Engagement": 40000.0,
            "Conversion": 20000.0,
        },
        "channels": ["TikTok", "Email", "TV"],
        "geographies": ["US", "CA"],
    }


class TestBudgetAllocator:
    """Tests for BudgetAllocator class."""

    def test_allocate_by_phase_correct_percentages(self, budget_allocator):
        """Should allocate 40/40/20 across phases."""
        result = budget_allocator.allocate_by_phase(100000.0)

        assert result["Awareness"] == 40000.0
        assert result["Engagement"] == 40000.0
        assert result["Conversion"] == 20000.0
        assert sum(result.values()) == 100000.0

    def test_allocate_by_phase_zero_budget(self, budget_allocator):
        """Should handle zero budget."""
        result = budget_allocator.allocate_by_phase(0.0)

        assert result["Awareness"] == 0.0
        assert result["Engagement"] == 0.0
        assert result["Conversion"] == 0.0

    def test_allocate_by_channel_equal_weights(self, budget_allocator):
        """Should distribute equally across channels with same weight."""
        channels = [
            {"channel": "TikTok", "weight": 1.0},
            {"channel": "Email", "weight": 1.0},
            {"channel": "TV", "weight": 1.0},
        ]
        result = budget_allocator.allocate_by_channel(30000.0, channels)

        assert result["TikTok"] == 10000.0
        assert result["Email"] == 10000.0
        assert result["TV"] == 10000.0

    def test_allocate_by_channel_weighted(self, budget_allocator):
        """Should distribute proportionally by weight."""
        channels = [
            {"channel": "TikTok", "weight": 2.0},
            {"channel": "Email", "weight": 1.0},
        ]
        result = budget_allocator.allocate_by_channel(30000.0, channels)

        assert result["TikTok"] == 20000.0
        assert result["Email"] == 10000.0

    def test_allocate_by_geography_equal_distribution(self, budget_allocator):
        """Should distribute equally across geographies."""
        geographies = ["US", "CA", "MX"]
        result = budget_allocator.allocate_by_geography(30000.0, geographies)

        assert result["US"] == 10000.0
        assert result["CA"] == 10000.0
        assert result["MX"] == 10000.0

    def test_calculate_contingency_default_10_percent(self, budget_allocator):
        """Should calculate 10% contingency by default."""
        result = budget_allocator.calculate_contingency(100000.0)
        assert result == 10000.0

    def test_calculate_contingency_custom_percentage(self, budget_allocator):
        """Should calculate custom contingency percentage."""
        result = budget_allocator.calculate_contingency(100000.0, pct=0.15)
        assert result == 15000.0


class TestActivationGenerator:
    """Tests for ActivationGenerator class."""

    def test_calculate_reach_has_cpm_rates(self, activation_generator):
        """Should have CPM rates for all channels."""
        assert len(activation_generator.CHANNEL_CPM_RATES) > 0
        assert "TikTok" in activation_generator.CHANNEL_CPM_RATES
        assert "Email" in activation_generator.CHANNEL_CPM_RATES

    def test_generate_activation_with_budget(self, activation_generator, sample_activation):
        """Should generate activation with cost calculations."""
        # Budget allocator would normally calculate reach based on CPM
        result = activation_generator.generate_activation(
            phase="Awareness",
            channel="TikTok",
            budget=10000.0,
            geographies=["US"],
            audience_segment="Primary",
        )

        assert result is not None
        assert "reach" in result or "budget" in result

    def test_cpm_calculation_consistency(self, activation_generator):
        """CPM rates should be consistent across channels."""
        # TikTok CPM should be lower than TV
        assert activation_generator.CHANNEL_CPM_RATES["TikTok"] < activation_generator.CHANNEL_CPM_RATES["TV"]
        # Email should be lowest cost
        assert activation_generator.CHANNEL_CPM_RATES["Email"] < activation_generator.CHANNEL_CPM_RATES["TV"]


class TestOfflineConstraintHandler:
    """Tests for OfflineConstraintHandler class."""

    def test_get_lead_time_tv(self, constraint_handler):
        """TV should have 28-day lead time."""
        result = constraint_handler.get_lead_time_days("TV")
        assert result == 28

    def test_get_lead_time_print(self, constraint_handler):
        """Print should have 14-day lead time."""
        result = constraint_handler.get_lead_time_days("Print")
        assert result == 14

    def test_get_lead_time_digital(self, constraint_handler):
        """Digital channels should have 3-day lead time."""
        result = constraint_handler.get_lead_time_days("TikTok")
        assert result == 3

    def test_validate_scheduled_date_respects_lead_time(self, constraint_handler):
        """Scheduled date should respect lead time constraints."""
        today = date.today()
        scheduled_start = (today + timedelta(days=35)).isoformat()

        result = constraint_handler.validate_lead_time_constraint(
            channel="TV",
            scheduled_start=scheduled_start,
        )
        assert result  # Should be valid (35 days > 28-day lead time)

    def test_validate_scheduled_date_fails_insufficient_lead_time(self, constraint_handler):
        """Should fail if lead time is insufficient."""
        today = date.today()
        scheduled_start = (today + timedelta(days=7)).isoformat()

        result = constraint_handler.validate_lead_time_constraint(
            channel="TV",
            scheduled_start=scheduled_start,
        )
        assert not result  # Should fail (7 days < 28-day lead time)


class TestActivationValidator:
    """Tests for ActivationValidator class."""

    def test_validate_activation_complete(self, validator, sample_activation):
        """Should validate complete activation."""
        errors = validator.validate(sample_activation)
        assert len(errors) == 0

    def test_validate_activation_missing_phase(self, validator, sample_activation):
        """Should detect missing phase."""
        sample_activation.pop("phase", None)
        errors = validator.validate(sample_activation)
        assert any("phase" in str(e).lower() for e in errors)

    def test_validate_activation_invalid_phase(self, validator, sample_activation):
        """Should detect invalid phase."""
        sample_activation["phase"] = "InvalidPhase"
        errors = validator.validate(sample_activation)
        assert len(errors) > 0

    def test_validate_activation_invalid_budget(self, validator, sample_activation):
        """Should detect invalid budget (negative)."""
        sample_activation["budget"] = -1000.0
        errors = validator.validate(sample_activation)
        assert len(errors) > 0


class TestMediaPlannerAgent:
    """Tests for media_planner_agent entry point."""

    @pytest.mark.asyncio
    async def test_media_planner_agent_happy_path(self, sample_campaign_context):
        """Should generate media plan from campaign context."""
        campaign_concept = {
            "id": "cc-001",
            "name": "Summer Campaign",
            "objective": "Increase brand awareness",
            "description": "Q2 campaign refresh",
            "target_audience": "18-45, urban",
            "timeline": "2 months",
        }

        budget_envelope = sample_campaign_context["budget_envelope"]

        result = await media_planner_agent(
            campaign_concept=campaign_concept,
            budget_envelope=budget_envelope,
            campaign_context=sample_campaign_context,
        )

        assert result is not None
        assert "activations" in result or "status" in result

    @pytest.mark.asyncio
    async def test_media_planner_agent_returns_valid_structure(self, sample_campaign_context):
        """Should return properly structured output."""
        campaign_concept = {
            "id": "cc-001",
            "name": "Test Campaign",
            "objective": "Test",
            "description": "Test",
            "target_audience": "Test",
            "timeline": "Test",
        }

        result = await media_planner_agent(
            campaign_concept=campaign_concept,
            budget_envelope=100000.0,
            campaign_context=sample_campaign_context,
        )

        assert isinstance(result, dict)
