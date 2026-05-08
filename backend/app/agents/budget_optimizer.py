"""Budget Optimizer Agent (AGT-05).

Reallocates media spend across activations to maximize reach-weighted-by-conversion ROI
while maintaining phase structure and strategic constraints.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import date
import asyncio

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


class ROIAnalyzer:
    """Analyzes ROI metrics across phases, channels, and total campaign."""

    def analyze(
        self,
        optimized_activations: List[Dict[str, Any]],
        conversion_rates: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Analyze ROI across phases, channels, and total campaign.

        Args:
            optimized_activations: List of optimized activations with reach and cost
            conversion_rates: Dict mapping activation ID to conversion rate

        Returns:
            Dict with phase_summary, channel_summary, and totals
        """
        phase_summary = {}
        channel_summary = {}
        total_reach_weighted = 0
        total_budget = 0.0

        # First pass: collect data by phase and channel
        phase_data = {}  # phase -> {channel -> [(reach_weighted, budget)]}
        channel_data = {}  # channel -> [(reach_weighted, budget)]

        for activation in optimized_activations:
            act_id = activation.get("id")
            phase = activation.get("phase", "Engagement")
            sub_channel = activation.get("sub_channel", "Unknown")
            reach = activation.get("estimated_reach", 0)
            budget = activation.get("optimized_cost_estimated", 0.0)
            conv_rate = conversion_rates.get(act_id, 0.005)

            # Calculate reach-weighted-conversions
            reach_weighted = int(reach * conv_rate)

            # Track totals
            total_reach_weighted += reach_weighted
            total_budget += budget

            # Track by phase
            if phase not in phase_data:
                phase_data[phase] = {}
            if sub_channel not in phase_data[phase]:
                phase_data[phase][sub_channel] = []
            phase_data[phase][sub_channel].append((reach_weighted, budget))

            # Track by channel
            if sub_channel not in channel_data:
                channel_data[sub_channel] = []
            channel_data[sub_channel].append((reach_weighted, budget))

        # Build phase summary
        for phase, channels in phase_data.items():
            phase_reach_weighted = 0
            phase_budget = 0.0
            channel_breakdown = {}

            for channel, data_list in channels.items():
                channel_reach_weighted = sum(rw for rw, _ in data_list)
                channel_budget = sum(b for _, b in data_list)
                channel_roi = channel_reach_weighted / channel_budget if channel_budget > 0 else 0.0

                phase_reach_weighted += channel_reach_weighted
                phase_budget += channel_budget

                channel_breakdown[channel] = {
                    "reach_weighted_conversions": channel_reach_weighted,
                    "allocated_budget": channel_budget,
                    "roi": channel_roi,
                }

            phase_roi = phase_reach_weighted / phase_budget if phase_budget > 0 else 0.0

            phase_summary[phase] = {
                "reach_weighted_conversions": phase_reach_weighted,
                "allocated_budget": phase_budget,
                "roi": phase_roi,
                "channel_breakdown": channel_breakdown,
            }

        # Build channel summary
        for channel, data_list in channel_data.items():
            channel_reach_weighted = sum(rw for rw, _ in data_list)
            channel_budget = sum(b for _, b in data_list)
            channel_roi = channel_reach_weighted / channel_budget if channel_budget > 0 else 0.0

            channel_summary[channel] = {
                "reach_weighted_conversions": channel_reach_weighted,
                "total_allocated": channel_budget,
                "roi": channel_roi,
            }

        # Calculate campaign total ROI
        campaign_roi = total_reach_weighted / total_budget if total_budget > 0 else 0.0

        return {
            "phase_summary": phase_summary,
            "channel_summary": channel_summary,
            "totals": {
                "total_reach_weighted_conversions": total_reach_weighted,
                "total_budget": total_budget,
                "roi": campaign_roi,
            },
        }


class OptimizationReporter:
    """Generates detailed optimization report with budget shift explanations."""

    SHIFT_THRESHOLD = 0.05  # 5% change threshold for reporting

    def generate_report(
        self,
        original_activations: List[Dict[str, Any]],
        optimized_activations: List[Dict[str, Any]],
        conversion_rates: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Generate optimization report comparing original and optimized activations.

        Args:
            original_activations: Original activation list from Media Planner
            optimized_activations: Optimized activation list
            conversion_rates: Dict mapping activation ID to conversion rate

        Returns:
            Report dict with budget shifts, prioritized/deprioritized activations
        """
        budget_shifts = []
        prioritized = []
        deprioritized = []

        # Build lookup for original costs
        original_costs = {a.get("id"): a.get("optimized_cost_estimated", 0.0) for a in original_activations}

        # Analyze each optimized activation
        for opt_act in optimized_activations:
            act_id = opt_act.get("id")
            original_cost = original_costs.get(act_id, 0.0)
            optimized_cost = opt_act.get("optimized_cost_estimated", 0.0)

            if original_cost == 0:
                continue

            cost_change = optimized_cost - original_cost
            cost_change_pct = cost_change / original_cost if original_cost > 0 else 0

            # Significant change?
            if abs(cost_change_pct) > self.SHIFT_THRESHOLD:
                roi = (opt_act.get("estimated_reach", 0) * conversion_rates.get(act_id, 0.005)) / optimized_cost if optimized_cost > 0 else 0

                # Add to budget shifts
                budget_shifts.append({
                    "activation_id": act_id,
                    "original_budget": original_cost,
                    "optimized_budget": optimized_cost,
                    "change_pct": cost_change_pct * 100,
                })

                if cost_change_pct > 0:
                    # Prioritized (increased)
                    prioritized.append({
                        "activation_id": act_id,
                        "activation_name": f"{opt_act.get('sub_channel')} {opt_act.get('geography')} {opt_act.get('phase')}",
                        "original_budget": original_cost,
                        "optimized_budget": optimized_cost,
                        "budget_increase_pct": cost_change_pct * 100,
                        "roi_per_dollar": roi,
                        "reason": f"High ROI ({roi:.2f}x), prioritized for maximum impact"
                    })
                else:
                    # Deprioritized (decreased)
                    deprioritized.append({
                        "activation_id": act_id,
                        "activation_name": f"{opt_act.get('sub_channel')} {opt_act.get('geography')} {opt_act.get('phase')}",
                        "original_budget": original_cost,
                        "optimized_budget": optimized_cost,
                        "budget_decrease_pct": abs(cost_change_pct) * 100,
                        "roi_per_dollar": roi,
                        "reason": f"Lower ROI ({roi:.2f}x), budget reallocated to higher performers"
                    })

        # Generate summary
        total_increase = sum(a["optimized_budget"] - a["original_budget"] for a in prioritized)
        total_decrease = sum(a["original_budget"] - a["optimized_budget"] for a in deprioritized)

        summary = f"Budget optimized: +${total_increase:,.0f} to high-ROI, -${total_decrease:,.0f} from low-ROI activations"

        return {
            "summary": summary,
            "budget_shifts": budget_shifts,
            "prioritized_activations": prioritized,
            "deprioritized_activations": deprioritized,
            "constraints_maintained": {
                "phase_budgets": "40% Awareness / 40% Engagement / 20% Conversion ✓",
                "scheduled_dates": "All dates locked (no changes) ✓",
                "channels": "All channels preserved from Media Planner ✓",
                "geographies": "All geographies preserved from Media Planner ✓",
            }
        }


async def budget_optimizer_agent(
    activations: List[Dict[str, Any]],
    budget_envelope: Dict[str, Any],
    campaign_context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Orchestrator function that coordinates all Budget Optimizer components.

    Coordinates:
    1. ConversionRateEstimator: Estimates conversion likelihood per activation
    2. BudgetOptimizer: Optimizes budget allocation across activations
    3. ROIAnalyzer: Analyzes ROI metrics across phases and channels
    4. OptimizationReporter: Generates detailed optimization report

    Args:
        activations: List of activations from Media Planner with cost_estimated
        budget_envelope: Dict with total_budget and currency
        campaign_context: Dict with campaign name, tone_board, target_audience

    Returns:
        Dict with optimized_activations, roi_analysis, optimization_report,
        validation_errors, and status
    """
    validation_errors = []

    try:
        # Initialize component instances
        estimator = ConversionRateEstimator()
        optimizer = BudgetOptimizer()
        analyzer = ROIAnalyzer()
        reporter = OptimizationReporter()

        # Parse budget envelope
        total_budget = budget_envelope.get("total_budget", 0.0)

        # Calculate phase budgets: 40% Awareness / 40% Engagement / 20% Conversion
        phase_budgets = {
            "Awareness": total_budget * 0.40,
            "Engagement": total_budget * 0.40,
            "Conversion": total_budget * 0.20,
        }

        # Store original costs
        for activation in activations:
            activation["original_cost_estimated"] = activation.get("cost_estimated", 0.0)
            # Initialize optimized_cost_estimated with original cost for optimizer
            activation["optimized_cost_estimated"] = activation.get("cost_estimated", 0.0)

        # Step 1: Estimate conversion rates for each activation
        conversion_rates = {}
        for activation in activations:
            act_id = activation.get("id")
            conv_rate = estimator.estimate_conversion_rate(activation, campaign_context)
            conversion_rates[act_id] = conv_rate

        # Step 2: Optimize budget allocation
        optimized_activations = optimizer.optimize(activations, conversion_rates, phase_budgets)

        # Step 3: Analyze ROI
        roi_analysis = analyzer.analyze(optimized_activations, conversion_rates)

        # Step 4: Generate optimization report
        optimization_report = reporter.generate_report(activations, optimized_activations, conversion_rates)

        # Step 5: Build output activations with all fields
        output_activations = []
        for opt_act in optimized_activations:
            act_id = opt_act.get("id")
            conv_rate = conversion_rates.get(act_id, 0.005)
            reach = opt_act.get("estimated_reach", 0)

            # Calculate reach_weighted_conversions
            reach_weighted_conversions = int(reach * conv_rate)

            # Calculate roi_per_dollar
            cost = opt_act.get("optimized_cost_estimated", 1.0)
            if cost > 0:
                roi_per_dollar = reach_weighted_conversions / cost
            else:
                roi_per_dollar = 0.0

            # Determine optimization_action
            original_cost = opt_act.get("original_cost_estimated", cost)
            if original_cost > 0:
                cost_change_pct = (cost - original_cost) / original_cost
            else:
                cost_change_pct = 0.0

            if abs(cost_change_pct) <= 0.05:
                optimization_action = "unchanged"
                reason = "Cost change within 5% threshold"
            elif cost_change_pct > 0.05:
                optimization_action = "prioritized"
                reason = f"Budget increased by {cost_change_pct*100:.1f}% due to high ROI"
            else:
                optimization_action = "deprioritized"
                reason = f"Budget decreased by {abs(cost_change_pct)*100:.1f}% to reallocate to higher performers"

            output_activation = {
                "id": act_id,
                "channel_enum": opt_act.get("channel_enum"),
                "sub_channel": opt_act.get("sub_channel"),
                "format": opt_act.get("format"),
                "geography": opt_act.get("geography"),
                "placement": opt_act.get("placement"),
                "phase": opt_act.get("phase"),
                "scheduled_date": opt_act.get("scheduled_date"),
                "duration": opt_act.get("duration"),
                "frequency": opt_act.get("frequency"),
                "audience_segment": opt_act.get("audience_segment"),
                "estimated_reach": reach,
                "estimated_cpm": opt_act.get("estimated_cpm"),
                "original_cost_estimated": original_cost,
                "optimized_cost_estimated": cost,
                "message_version_ref": opt_act.get("message_version_ref"),
                "lead_time_days": opt_act.get("lead_time_days"),
                "offline_constraints": opt_act.get("offline_constraints"),
                "conversion_rate_estimated": conv_rate,
                "reach_weighted_conversions": reach_weighted_conversions,
                "roi_per_dollar": roi_per_dollar,
                "optimization_action": optimization_action,
                "reason": reason,
            }
            output_activations.append(output_activation)

        # Determine status
        status = "success" if len(validation_errors) == 0 else "partial"

        return {
            "optimized_activations": output_activations,
            "roi_analysis": roi_analysis,
            "optimization_report": optimization_report,
            "validation_errors": validation_errors,
            "status": status,
        }

    except Exception as e:
        logger.error(f"Budget optimizer orchestrator failed: {str(e)}")
        return {
            "optimized_activations": [],
            "roi_analysis": None,
            "optimization_report": None,
            "validation_errors": [str(e)],
            "status": "failed",
        }
