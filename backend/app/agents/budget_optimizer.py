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
