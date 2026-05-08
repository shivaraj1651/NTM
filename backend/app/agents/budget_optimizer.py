"""Budget Optimizer Agent (AGT-05).

Reallocates media spend across activations to maximize reach-weighted-by-conversion ROI
while maintaining phase structure and strategic constraints.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import date

logger = logging.getLogger(__name__)


class ConversionRateEstimator:
    """Estimates conversion likelihood per activation."""

    # Base conversion rates by channel (0.1% to 3%)
    CHANNEL_BASE_RATES = {
        "TikTok": 0.008,      # 0.8%
        "Instagram": 0.006,   # 0.6%
        "Facebook": 0.005,    # 0.5%
        "Google Search": 0.015,  # 1.5%
        "Display": 0.003,     # 0.3%
        "Email": 0.030,       # 3.0%
        "WhatsApp": 0.020,    # 2.0%
        "Influencer": 0.012,  # 1.2%
        "Print": 0.002,       # 0.2%
        "OOH": 0.001,         # 0.1%
        "Radio": 0.004,       # 0.4%
        "TV": 0.002,          # 0.2%
        "Events": 0.010,      # 1.0%
        "Cinema": 0.003,      # 0.3%
        "Direct Mail": 0.005, # 0.5%
    }

    # Segment multipliers (Primary > Secondary > Tertiary)
    SEGMENT_MULTIPLIERS = {
        "Primary": 1.0,
        "Secondary": 0.7,
        "Tertiary": 0.4,
    }

    # Phase multipliers (Conversion > Engagement > Awareness)
    PHASE_MULTIPLIERS = {
        "Awareness": 0.5,
        "Engagement": 1.0,
        "Conversion": 1.5,
    }

    def estimate_conversion_rate(
        self,
        activation: Dict[str, Any],
        campaign_context: Dict[str, Any],
        historical_data: Optional[Dict[str, float]] = None
    ) -> float:
        """
        Estimate conversion likelihood for an activation.

        Args:
            activation: Activation dict with sub_channel, audience_segment, phase
            campaign_context: Campaign context with tone_board
            historical_data: Optional historical conversion rates

        Returns:
            Estimated conversion rate (0.001 - 0.10)
        """
        sub_channel = activation.get("sub_channel", "Email")
        segment = activation.get("audience_segment", "Primary")
        phase = activation.get("phase", "Engagement")

        # Try historical data first
        if historical_data and sub_channel in historical_data:
            base_rate = historical_data[sub_channel]
        else:
            # Fallback to channel defaults
            base_rate = self.CHANNEL_BASE_RATES.get(sub_channel, 0.005)

        # Apply segment multiplier
        segment_mult = self.SEGMENT_MULTIPLIERS.get(segment, 1.0)

        # Apply phase multiplier
        phase_mult = self.PHASE_MULTIPLIERS.get(phase, 1.0)

        # Calculate estimated rate
        estimated_rate = base_rate * segment_mult * phase_mult

        # Clamp to valid range [0.001, 0.10]
        estimated_rate = max(0.001, min(0.10, estimated_rate))

        return estimated_rate


class BudgetOptimizer:
    """Optimizes budget allocation across activations to maximize ROI."""

    MIN_ACTIVATION_BUDGET = 100.0

    def calculate_roi_per_dollar(self, activation: Dict[str, Any], conversion_rate: float) -> float:
        """
        Calculate ROI per dollar (reach-weighted-conversions / cost).

        Args:
            activation: Activation dict with estimated_reach and optimized_cost_estimated
            conversion_rate: Estimated conversion rate

        Returns:
            ROI metric (reach-weighted-conversions per $1)
        """
        reach = activation.get("estimated_reach", 0)
        cost = activation.get("optimized_cost_estimated", 1.0)

        if cost == 0:
            cost = 1.0

        reach_weighted = reach * conversion_rate
        return reach_weighted / cost

    def optimize(
        self,
        activations: List[Dict[str, Any]],
        conversion_rates: Dict[str, float],
        phase_budgets: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        Optimize budget allocation across activations.

        Args:
            activations: List of activations to optimize
            conversion_rates: Dict mapping activation ID to conversion rate
            phase_budgets: Dict with total budget per phase

        Returns:
            Optimized activation list with adjusted costs
        """
        optimized = []

        # Group activations by phase
        by_phase = {}
        for activation in activations:
            phase = activation.get("phase", "Engagement")
            if phase not in by_phase:
                by_phase[phase] = []
            by_phase[phase].append(activation)

        # Optimize each phase independently
        for phase, phase_activations in by_phase.items():
            phase_budget = phase_budgets.get(phase, 0.0)

            # Calculate ROI per dollar for each activation
            roi_scores = {}
            for act in phase_activations:
                act_id = act.get("id")
                conv_rate = conversion_rates.get(act_id, 0.005)
                roi = self.calculate_roi_per_dollar(act, conv_rate)
                roi_scores[act_id] = roi

            # Sort by ROI (highest first)
            sorted_ids = sorted(roi_scores.keys(), key=lambda x: roi_scores[x], reverse=True)

            # Allocate budget greedily
            remaining_budget = phase_budget
            allocations = {}

            # First pass: allocate to high-ROI activations
            for act_id in sorted_ids:
                act = next(a for a in phase_activations if a["id"] == act_id)
                original_cost = act.get("optimized_cost_estimated", 1000.0)

                # Allocate more to high-ROI, less to low-ROI
                roi = roi_scores[act_id]
                total_roi = sum(roi_scores.values())

                # Proportional allocation based on ROI
                roi_share = roi / total_roi if total_roi > 0 else 1.0 / len(sorted_ids)
                allocated = phase_budget * roi_share

                # Enforce minimum
                allocated = max(self.MIN_ACTIVATION_BUDGET, allocated)

                allocations[act_id] = allocated
                remaining_budget -= allocated

            # Adjust if total exceeds budget
            total_allocated = sum(allocations.values())
            if total_allocated > phase_budget:
                scale_factor = phase_budget / total_allocated
                for act_id in allocations:
                    allocations[act_id] *= scale_factor

            # Build optimized activations for this phase
            for act in phase_activations:
                act_id = act.get("id")
                optimized_cost = allocations.get(act_id, act.get("optimized_cost_estimated", 0.0))

                optimized_act = act.copy()
                optimized_act["optimized_cost_estimated"] = optimized_cost
                optimized.append(optimized_act)

        return optimized
