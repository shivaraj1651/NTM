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
