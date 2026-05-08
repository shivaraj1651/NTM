"""Media Planner Agent (AGT-04).

Transforms approved campaign concepts and budgets into detailed Activation Master Plans.
Uses top-down budget allocation: phases → channels → geographies.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import date, timedelta
from pydantic import ValidationError
from backend.app.schemas.media_plan import Activation, PhaseEnum, ChannelEnum, AudienceSegmentEnum

logger = logging.getLogger(__name__)


class BudgetAllocator:
    """Allocates budget across phases, channels, and geographies."""

    def allocate_by_phase(self, total_budget: float) -> Dict[str, float]:
        """
        Allocate budget across phases: Awareness 40%, Engagement 40%, Conversion 20%.

        Args:
            total_budget: Total budget envelope

        Returns:
            Dict with phase names as keys, allocated amounts as values
        """
        return {
            "Awareness": total_budget * 0.40,
            "Engagement": total_budget * 0.40,
            "Conversion": total_budget * 0.20,
        }

    def allocate_by_channel(self, phase_budget: float, channels: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Allocate phase budget across channels by weight.

        Args:
            phase_budget: Budget for this phase
            channels: List of channel dicts with 'channel' name and optional 'weight'

        Returns:
            Dict with channel names as keys, allocated amounts as values
        """
        allocations = {}

        # Extract weights or use equal distribution
        total_weight = 0.0
        for ch in channels:
            weight = ch.get("weight", 1.0)
            total_weight += weight

        for ch in channels:
            weight = ch.get("weight", 1.0)
            channel_name = ch["channel"]
            allocated = phase_budget * (weight / total_weight)
            allocations[channel_name] = allocated

        return allocations

    def allocate_by_geography(self, channel_budget: float, geographies: List[str]) -> Dict[str, float]:
        """
        Allocate channel budget equally across geographies.

        Args:
            channel_budget: Budget for this channel/phase
            geographies: List of markets/regions

        Returns:
            Dict with geography names as keys, allocated amounts as values
        """
        per_geography = channel_budget / len(geographies)
        return {geo: per_geography for geo in geographies}

    def calculate_contingency(self, total_spend: float, pct: float = 0.10) -> float:
        """
        Calculate contingency reserve (10% of total spend by default).

        Args:
            total_spend: Total amount spent on activations
            pct: Contingency percentage (default 0.10 = 10%)

        Returns:
            Contingency reserve amount
        """
        return total_spend * pct


class ActivationGenerator:
    """Generates activation details with reach, cost, frequency, and CPM calculations."""

    # CPM rates per channel (cost per thousand impressions)
    CHANNEL_CPM_RATES = {
        "TikTok": 5.0,
        "Instagram": 8.0,
        "Facebook": 7.0,
        "YouTube": 10.0,
        "TV": 20.0,
        "Email": 0.50,
        "Radio": 12.0,
        "Print": 15.0,
    }

    # Penetration rates per phase
    PHASE_PENETRATION = {
        "Awareness": 0.60,
        "Engagement": 0.30,
        "Conversion": 0.10,
    }

    # Frequency per phase (ad exposures)
    PHASE_FREQUENCY = {
        "Awareness": "3x daily",
        "Engagement": "2x daily",
        "Conversion": "1x daily",
    }

    def calculate_reach(self, audience_size: int, penetration_pct: float) -> int:
        """
        Calculate reach as audience_size × penetration_pct.

        Args:
            audience_size: Total audience size
            penetration_pct: Penetration percentage as decimal (e.g., 0.25 = 25%)

        Returns:
            Reach count (rounded to int)
        """
        return int(audience_size * penetration_pct)

    def calculate_cost(self, reach: int, cpm: float) -> float:
        """
        Calculate cost as (reach / 1000) × CPM.

        Args:
            reach: Number of people reached
            cpm: Cost per thousand impressions

        Returns:
            Cost in currency units
        """
        return (reach / 1000.0) * cpm

    def get_frequency_for_phase(self, phase: str) -> str:
        """
        Get frequency string for a phase.

        Args:
            phase: Phase name (Awareness, Engagement, or Conversion)

        Returns:
            Frequency string (e.g., "3x daily")
        """
        return self.PHASE_FREQUENCY.get(phase, "1x daily")

    def get_cpm_for_channel(self, channel_name: str) -> float:
        """
        Get CPM rate for a channel.

        Args:
            channel_name: Channel name

        Returns:
            CPM rate (default 10.0 if channel not found)
        """
        return self.CHANNEL_CPM_RATES.get(channel_name, 10.0)

    def get_penetration_for_phase(self, phase: str) -> float:
        """
        Get penetration rate for a phase.

        Args:
            phase: Phase name (Awareness, Engagement, or Conversion)

        Returns:
            Penetration rate as decimal (default 0.0)
        """
        return self.PHASE_PENETRATION.get(phase, 0.0)


class OfflineConstraintHandler:
    """Manages lead time constraints for offline channels."""

    # Lead time (days) for each offline channel
    OFFLINE_LEAD_TIMES = {
        "TV": 28,           # 4 weeks
        "Print": 14,        # 2 weeks
        "Cinema": 21,       # 3 weeks
        "Radio": 10,        # ~1.5 weeks
        "Events": 14,       # 2 weeks
        "DirectMail": 14,   # 2 weeks
        "OOH": 7,           # 1 week
    }

    # Set of offline channel names
    OFFLINE_CHANNELS = set(OFFLINE_LEAD_TIMES.keys())

    def is_offline(self, channel_name: str) -> bool:
        """
        Check if a channel is offline.

        Args:
            channel_name: Channel name

        Returns:
            True if channel is offline, False if online
        """
        return channel_name in self.OFFLINE_CHANNELS

    def get_lead_time_days(self, channel_name: str) -> int:
        """
        Get lead time for a channel.

        Args:
            channel_name: Channel name

        Returns:
            Lead time in days (0 for online channels)
        """
        return self.OFFLINE_LEAD_TIMES.get(channel_name, 0)

    def calculate_scheduled_date(self, channel_name: str, phase_start: date) -> date:
        """
        Calculate scheduled date for a channel considering lead time.

        Args:
            channel_name: Channel name
            phase_start: Phase start date

        Returns:
            Scheduled date (phase_start minus lead_time)
        """
        lead_time_days = self.get_lead_time_days(channel_name)
        return phase_start - timedelta(days=lead_time_days)

    def get_offline_constraints_note(self, channel_name: str) -> Optional[str]:
        """
        Get human-readable constraint note for a channel.

        Args:
            channel_name: Channel name

        Returns:
            Constraint note string or None if online
        """
        if not self.is_offline(channel_name):
            return None

        lead_time = self.get_lead_time_days(channel_name)
        if lead_time == 0:
            return None

        weeks = lead_time // 7
        if lead_time % 7 == 0 and weeks > 0:
            week_str = f"{weeks} week" if weeks == 1 else f"{weeks} weeks"
            return f"Requires {week_str} lead time"
        else:
            return f"Requires {lead_time} days lead time"


class ActivationValidator:
    """Validates Activation objects against the Pydantic schema."""

    def validate_schema(self, activation_dict: dict) -> List[str]:
        """
        Validate an activation dictionary against the Activation Pydantic schema.

        Args:
            activation_dict: Dictionary containing activation data

        Returns:
            List of error strings. Empty list if valid. Each error formatted as
            "Field 'field_path': error_message"
        """
        try:
            Activation(**activation_dict)
            return []
        except ValidationError as e:
            errors = []
            for error in e.errors():
                # error is a dict with 'loc' (field path tuple) and 'msg'
                field_path = ".".join(str(loc) for loc in error["loc"])
                message = error["msg"]
                errors.append(f"Field '{field_path}': {message}")
            return errors


async def media_planner_agent(
    campaign_concept: Dict[str, Any],
    budget_envelope: Dict[str, Any],
    mandate_geography: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Main orchestrator: coordinates allocation, generation, constraints, validation.

    Transforms a campaign concept and budget into a detailed Activation Master Plan
    using top-down budget allocation: phases → channels → geographies.

    Args:
        campaign_concept: Campaign concept dict with channel_mix, campaign_phasing, tone_board, message_architecture
        budget_envelope: Budget dict with total_budget, currency, contingency_pct
        mandate_geography: Geography dict with regions, markets, countries

    Returns:
        Dict with:
          - activations: List of Activation objects (validated)
          - budget_summary: BudgetSummary with phase/channel/contingency breakdown
          - validation_errors: List of validation error strings
          - allocation_log: List of allocation decision log entries
          - status: "success" (all valid), "partial" (some valid), or "failed" (none valid)
    """
    # Initialize component instances
    allocator = BudgetAllocator()
    generator = ActivationGenerator()
    constraint_handler = OfflineConstraintHandler()
    validator = ActivationValidator()

    # Extract inputs
    total_budget = budget_envelope.get("total_budget", 100000.0)
    currency = budget_envelope.get("currency", "USD")
    contingency_pct = budget_envelope.get("contingency_pct", 0.10)
    markets = mandate_geography.get("markets", [])
    channels = campaign_concept.get("channel_mix", [])
    campaign_phasing = campaign_concept.get("campaign_phasing", {})
    tone_board = campaign_concept.get("tone_board", {})
    message_architecture = campaign_concept.get("message_architecture", {})

    # Initialize tracking
    activations = []
    validation_errors = []
    allocation_log = []
    total_spent = 0.0
    channel_activation_counts = {}
    phase_breakdown_tracking = {}
    channel_breakdown_tracking = {}

    # Phase allocation (40% Awareness, 40% Engagement, 20% Conversion)
    phase_budgets = allocator.allocate_by_phase(total_budget)
    allocation_log.append(f"Phase budget allocation: Awareness={phase_budgets['Awareness']:.2f}, "
                         f"Engagement={phase_budgets['Engagement']:.2f}, "
                         f"Conversion={phase_budgets['Conversion']:.2f}")

    # For each phase, allocate to channels and geographies
    for phase_name, phase_budget in phase_budgets.items():
        phase_breakdown_tracking[phase_name] = {
            "allocated": phase_budget,
            "spent": 0.0,
            "remaining": phase_budget
        }

        # Allocate phase budget to channels
        channel_budgets = allocator.allocate_by_channel(phase_budget, channels)
        allocation_log.append(f"{phase_name} channel allocation: {channel_budgets}")

        # For each channel in this phase
        for channel_dict in channels:
            channel_name = channel_dict.get("channel", "Unknown")
            channel_budget = channel_budgets.get(channel_name, 0.0)

            if channel_name not in channel_activation_counts:
                channel_activation_counts[channel_name] = 0
            if channel_name not in channel_breakdown_tracking:
                channel_breakdown_tracking[channel_name] = {
                    "allocated": 0.0,
                    "spent": 0.0,
                    "activations_count": 0
                }

            channel_breakdown_tracking[channel_name]["allocated"] += channel_budget

            # Get phase start date for offline constraint calculation
            phase_dates = campaign_phasing.get(phase_name, {})
            phase_start = phase_dates.get("start", date.today())

            # For each market in this channel/phase
            for market in markets:
                # Allocate channel budget equally across markets
                market_budget = channel_budget / len(markets) if markets else 0.0

                # Calculate activation details
                audience_size = 2000000  # Assumed market audience
                penetration = generator.get_penetration_for_phase(phase_name)
                estimated_reach = generator.calculate_reach(audience_size, penetration)

                cpm = generator.get_cpm_for_channel(channel_name)
                estimated_cost = generator.calculate_cost(estimated_reach, cpm)

                # Cap cost to market budget to prevent overspending
                if estimated_cost > market_budget:
                    estimated_cost = market_budget

                # Map channel name to ChannelEnum
                channel_enum = ChannelEnum.SOCIAL
                if "Facebook" in channel_name or "Instagram" in channel_name or "TikTok" in channel_name:
                    channel_enum = ChannelEnum.SOCIAL
                elif "Email" in channel_name:
                    channel_enum = ChannelEnum.EMAIL
                elif "YouTube" in channel_name:
                    channel_enum = ChannelEnum.DISPLAY
                elif "TV" in channel_name:
                    channel_enum = ChannelEnum.TV
                elif "Radio" in channel_name:
                    channel_enum = ChannelEnum.RADIO
                elif "Print" in channel_name:
                    channel_enum = ChannelEnum.PRINT

                # Calculate scheduled date (accounting for offline lead time)
                scheduled_date = constraint_handler.calculate_scheduled_date(channel_name, phase_start)

                # Get offline constraint note
                offline_constraints = constraint_handler.get_offline_constraints_note(channel_name)
                lead_time_days = constraint_handler.get_lead_time_days(channel_name)

                # Determine frequency for this phase
                frequency = generator.get_frequency_for_phase(phase_name)

                # Build message version reference from tone board and message architecture
                tone_str = tone_board.get("tone", "standard")
                message_str = message_architecture.get("primary", "standard")
                message_version_ref = f"{channel_name} ({tone_str}) - {message_str}"

                # Build activation dictionary
                activation_dict = {
                    "channel_enum": channel_enum,
                    "sub_channel": channel_name,
                    "format": f"Standard format for {channel_name}",
                    "geography": market,
                    "placement": f"{channel_name} placement",
                    "phase": PhaseEnum(phase_name),
                    "scheduled_date": scheduled_date,
                    "duration": 14,  # Default 2-week duration
                    "frequency": frequency,
                    "audience_segment": AudienceSegmentEnum.PRIMARY,
                    "estimated_reach": estimated_reach,
                    "estimated_cpm": cpm,
                    "cost_estimated": estimated_cost,
                    "message_version_ref": message_version_ref,
                    "lead_time_days": lead_time_days if lead_time_days > 0 else None,
                    "offline_constraints": offline_constraints
                }

                # Validate activation
                errors = validator.validate_schema(activation_dict)

                if not errors:
                    # Valid activation - add to list and update tracking
                    activations.append(Activation(**activation_dict))
                    total_spent += estimated_cost
                    channel_activation_counts[channel_name] += 1
                    channel_breakdown_tracking[channel_name]["spent"] += estimated_cost
                    channel_breakdown_tracking[channel_name]["activations_count"] += 1
                    phase_breakdown_tracking[phase_name]["spent"] += estimated_cost
                else:
                    # Invalid activation - log errors
                    validation_errors.extend(errors)
                    allocation_log.append(f"Validation failed for {channel_name}/{market}/{phase_name}: {errors}")

    # Update remaining amounts
    for phase_name in phase_breakdown_tracking:
        phase_breakdown_tracking[phase_name]["remaining"] = (
            phase_breakdown_tracking[phase_name]["allocated"] - phase_breakdown_tracking[phase_name]["spent"]
        )

    # Calculate contingency
    contingency_allocated = total_budget - sum(p["allocated"] for p in phase_breakdown_tracking.values())
    contingency_used = allocator.calculate_contingency(total_spent, contingency_pct)
    contingency_remaining = contingency_allocated - contingency_used

    # Build budget summary
    budget_summary = {
        "total_budget": total_budget,
        "currency": currency,
        "phase_breakdown": phase_breakdown_tracking,
        "channel_breakdown": channel_breakdown_tracking,
        "contingency": {
            "allocated": contingency_allocated,
            "used": contingency_used,
            "remaining": contingency_remaining
        },
        "total_spent": total_spent,
        "total_remaining": total_budget - total_spent,
        "utilization_pct": (total_spent / total_budget * 100) if total_budget > 0 else 0.0
    }

    # Determine status
    if len(validation_errors) == 0:
        status = "success"
    elif len(activations) > 0:
        status = "partial"
    else:
        status = "failed"

    # Build and return response
    response = {
        "activations": activations,
        "budget_summary": budget_summary,
        "validation_errors": validation_errors,
        "allocation_log": allocation_log,
        "status": status
    }

    logger.info(f"Media planner generated {len(activations)} activations with status={status}")

    return response
