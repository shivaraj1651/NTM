"""Media Planner Agent (AGT-04).

Transforms approved campaign concepts and budgets into detailed Activation Master Plans.
Uses top-down budget allocation: phases → channels → geographies.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import date, timedelta

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
