"""Budget Optimizer Agent (AGT-05).

Reallocates media spend across activations to maximize reach-weighted-by-conversion ROI
while maintaining phase structure and strategic constraints.

Uses an LLM intelligence layer to derive context-aware phase weights, channel priorities,
and executive narrative — ensuring each mandate produces a unique, tailored budget plan.
"""

import json
import logging
from typing import Any

from anthropic import AsyncAnthropic

from backend.app.agents.json_parsing import extract_json
from backend.app.external.stubs import stub_enabled

logger = logging.getLogger(__name__)


# ── LLM Intelligence Layer ────────────────────────────────────────────────────

async def _generate_optimization_intelligence(
    activations: list[dict[str, Any]],
    budget_envelope: dict[str, Any],
    campaign_context: dict[str, Any],
) -> dict[str, Any]:
    """
    Call Claude to produce context-aware budget optimization strategy.

    Returns:
        - phase_weights: Relative importance of each phase for this specific mandate
        - channel_priorities: Ranked list of channels (most→least strategic)
        - audience_conversion_adjustments: Per-channel conversion rate tweaks (multipliers)
        - executive_summary: Mandate-specific narrative for the optimization
    Falls back to defaults on any error.
    """
    client = AsyncAnthropic()

    objective   = campaign_context.get("objective", "awareness")
    description = campaign_context.get("description", "")
    audience    = campaign_context.get("target_audience", "general consumers")
    total_budget = budget_envelope.get("total_budget", 100000)
    currency    = budget_envelope.get("currency", "USD")

    # Build channel/phase summary for the LLM
    channel_counts: dict[str, int] = {}
    phase_budgets_raw: dict[str, float] = {}
    for act in activations:
        ch = act.get("sub_channel", "Unknown")
        ph = act.get("phase", "Engagement")
        channel_counts[ch] = channel_counts.get(ch, 0) + 1
        phase_budgets_raw[ph] = phase_budgets_raw.get(ph, 0) + act.get("cost_estimated", 0)

    prompt = f"""You are a senior performance marketing strategist.
Analyse this campaign and produce a precise budget optimisation strategy.

CAMPAIGN BRIEF
  Objective : {objective}
  Description: {description}
  Target audience: {audience}
  Total budget: {currency} {total_budget:,.0f}
  Channel mix: {json.dumps(channel_counts)}
  Current phase budget distribution: {json.dumps({k: round(v, 2) for k, v in phase_budgets_raw.items()})}

Return ONLY valid JSON (no markdown, no code fences):
{{
  "phase_weights": {{
    "Awareness": <float 0-2>,
    "Engagement": <float 0-2>,
    "Conversion": <float 0-2>
  }},
  "channel_priorities": [<channel names in strategic priority order, most important first>],
  "audience_conversion_adjustments": {{
    "<channel_name>": <float multiplier, e.g. 1.3 = 30% uplift, 0.7 = 30% reduction>
  }},
  "executive_summary": "<3-4 sentences. Reference the specific objective, audience, and channels. Explain WHY the budget is being shifted the way it is.>"
}}

Guidelines:
- phase_weights express RELATIVE priority, not percentages (they will be normalised)
- For {objective} objective: weight the most relevant phase(s) higher
- channel_priorities: rank ALL channels listed in the channel mix
- audience_conversion_adjustments: adjust channels that are particularly suited or poorly suited for {audience}
- executive_summary MUST reference '{objective}', the audience '{audience}', and name at least 2 specific channels
"""

    # NTM_STUB_EXTERNAL: stubbed external call
    if stub_enabled():
        logger.info("Budget optimizer LLM stubbed (NTM_STUB_EXTERNAL)")
        return {
            "phase_weights": {"Awareness": 1.0, "Engagement": 1.0, "Conversion": 1.0},
            "channel_priorities": [],
            "audience_conversion_adjustments": {},
            "executive_summary": "Stub: budget optimization intelligence (NTM_STUB_EXTERNAL).",
        }

    try:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        intelligence = extract_json(raw)
        logger.info("Budget optimizer LLM intelligence generated successfully")
        return intelligence
    except Exception as e:
        logger.warning(f"Budget optimizer LLM call failed ({e}), using defaults")
        objective_phase_defaults = {
            "awareness":     {"Awareness": 1.5, "Engagement": 1.0, "Conversion": 0.5},
            "consideration": {"Awareness": 1.0, "Engagement": 1.5, "Conversion": 0.8},
            "conversion":    {"Awareness": 0.5, "Engagement": 1.0, "Conversion": 1.8},
            "loyalty":       {"Awareness": 0.5, "Engagement": 1.5, "Conversion": 1.2},
            "engagement":    {"Awareness": 0.8, "Engagement": 1.8, "Conversion": 0.7},
        }
        channels = list(channel_counts.keys())
        return {
            "phase_weights": objective_phase_defaults.get(
                objective, {"Awareness": 1.0, "Engagement": 1.0, "Conversion": 1.0}
            ),
            "channel_priorities": channels,
            "audience_conversion_adjustments": {ch: 1.0 for ch in channels},
            "executive_summary": (
                f"Budget optimisation for {objective} campaign targeting {audience}. "
                "Allocation follows standard phase weighting with ROI-proportional distribution."
            ),
        }


# ── Conversion Rate Estimator ─────────────────────────────────────────────────

class ConversionRateEstimator:
    """Estimates conversion likelihood per activation."""

    CHANNEL_BASE_RATES = {
        "TikTok": 0.008, "Instagram": 0.006, "Facebook": 0.005,
        "Google Search": 0.015, "Google Ads": 0.014,
        "Display": 0.003, "Email": 0.030, "WhatsApp": 0.020,
        "Influencer": 0.012, "LinkedIn": 0.009,
        "Print": 0.002, "OOH": 0.001, "Radio": 0.004,
        "TV": 0.002, "Events": 0.010, "Cinema": 0.003, "Direct Mail": 0.005,
        "YouTube": 0.007, "Twitter": 0.004, "Snapchat": 0.005,
    }

    SEGMENT_MULTIPLIERS = {"Primary": 1.0, "Secondary": 0.7, "Tertiary": 0.4}
    PHASE_MULTIPLIERS   = {"Awareness": 0.5, "Engagement": 1.0, "Conversion": 1.5}

    def estimate_conversion_rate(
        self,
        activation: dict[str, Any],
        campaign_context: dict[str, Any],
        historical_data: dict[str, float] | None = None,
        channel_adjustment: float = 1.0,
    ) -> float:
        sub_channel = activation.get("sub_channel", "Email")
        segment     = activation.get("audience_segment", "Primary")
        phase       = activation.get("phase", "Engagement")

        base_rate = (historical_data or {}).get(sub_channel) or self.CHANNEL_BASE_RATES.get(sub_channel, 0.005)
        segment_mult = self.SEGMENT_MULTIPLIERS.get(segment, 1.0)
        phase_mult   = self.PHASE_MULTIPLIERS.get(phase, 1.0)

        estimated = base_rate * segment_mult * phase_mult * channel_adjustment
        return max(0.001, min(0.10, estimated))


# ── Budget Optimizer ──────────────────────────────────────────────────────────

class BudgetOptimizer:
    """Optimises budget allocation across activations to maximise ROI."""

    MIN_ACTIVATION_BUDGET = 100.0

    def calculate_roi_per_dollar(self, activation: dict[str, Any], conversion_rate: float) -> float:
        reach = activation.get("estimated_reach", 0)
        cost  = max(activation.get("optimized_cost_estimated", 1.0), 1.0)
        return (reach * conversion_rate) / cost

    def optimize(
        self,
        activations: list[dict[str, Any]],
        conversion_rates: dict[str, float],
        phase_budgets: dict[str, float],
        channel_priority_order: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Optimise budget per phase, respecting channel priority order."""
        optimized = []
        by_phase: dict[str, list[dict]] = {}
        for act in activations:
            phase = act.get("phase", "Engagement")
            by_phase.setdefault(phase, []).append(act)

        for phase, phase_acts in by_phase.items():
            phase_budget = phase_budgets.get(phase, 0.0)

            roi_scores = {
                act["id"]: self.calculate_roi_per_dollar(act, conversion_rates.get(act["id"], 0.005))
                for act in phase_acts
            }

            # Boost score for high-priority channels
            if channel_priority_order:
                priority_boost = {ch: 1.0 + (len(channel_priority_order) - i) * 0.05
                                  for i, ch in enumerate(channel_priority_order)}
                for act in phase_acts:
                    act_id = act["id"]
                    ch     = act.get("sub_channel", "")
                    boost  = priority_boost.get(ch, 1.0)
                    roi_scores[act_id] = roi_scores[act_id] * boost

            total_roi = sum(roi_scores.values()) or 1.0
            allocations = {}

            for act in phase_acts:
                act_id   = act["id"]
                roi_share = roi_scores[act_id] / total_roi
                allocated = max(self.MIN_ACTIVATION_BUDGET, phase_budget * roi_share)
                allocations[act_id] = allocated

            # Rescale to fit phase budget
            total_alloc = sum(allocations.values())
            if total_alloc > phase_budget:
                scale = phase_budget / total_alloc
                allocations = {k: v * scale for k, v in allocations.items()}

            for act in phase_acts:
                opt = act.copy()
                opt["optimized_cost_estimated"] = allocations.get(act["id"], act.get("optimized_cost_estimated", 0.0))
                optimized.append(opt)

        return optimized


# ── ROI Analyser ──────────────────────────────────────────────────────────────

class ROIAnalyzer:
    """Analyses ROI metrics across phases, channels, and total campaign."""

    def analyze(self, optimized_activations: list[dict[str, Any]], conversion_rates: dict[str, float]) -> dict[str, Any]:
        phase_data: dict   = {}
        channel_data: dict = {}
        total_rw, total_budget = 0, 0.0

        for act in optimized_activations:
            act_id     = act.get("id")
            phase      = act.get("phase", "Engagement")
            sub_ch     = act.get("sub_channel", "Unknown")
            reach      = act.get("estimated_reach", 0)
            budget     = act.get("optimized_cost_estimated", 0.0)
            conv_rate  = conversion_rates.get(act_id, 0.005)
            rw         = int(reach * conv_rate)

            total_rw     += rw
            total_budget += budget

            phase_data.setdefault(phase, {}).setdefault(sub_ch, []).append((rw, budget))
            channel_data.setdefault(sub_ch, []).append((rw, budget))

        phase_summary = {}
        for phase, channels in phase_data.items():
            p_rw, p_budget = 0, 0.0
            ch_breakdown = {}
            for ch, data in channels.items():
                c_rw = sum(r for r, _ in data)
                c_b  = sum(b for _, b in data)
                p_rw += c_rw
                p_budget += c_b
                ch_breakdown[ch] = {"reach_weighted_conversions": c_rw, "allocated_budget": c_b, "roi": c_rw / c_b if c_b else 0}
            phase_summary[phase] = {
                "reach_weighted_conversions": p_rw, "allocated_budget": p_budget,
                "roi": p_rw / p_budget if p_budget else 0, "channel_breakdown": ch_breakdown,
            }

        channel_summary = {
            ch: {
                "reach_weighted_conversions": sum(r for r, _ in data),
                "total_allocated":            sum(b for _, b in data),
                "roi": sum(r for r, _ in data) / sum(b for _, b in data) if sum(b for _, b in data) else 0,
            }
            for ch, data in channel_data.items()
        }

        return {
            "phase_summary":   phase_summary,
            "channel_summary": channel_summary,
            "totals": {
                "total_reach_weighted_conversions": total_rw,
                "total_budget": total_budget,
                "roi": total_rw / total_budget if total_budget else 0,
            },
        }


# ── Optimisation Reporter ─────────────────────────────────────────────────────

class OptimizationReporter:
    """Generates detailed optimisation report with budget shift explanations."""

    SHIFT_THRESHOLD = 0.05

    def generate_report(
        self,
        original_activations: list[dict[str, Any]],
        optimized_activations: list[dict[str, Any]],
        conversion_rates: dict[str, float],
        executive_summary: str = "",
    ) -> dict[str, Any]:
        original_costs = {a.get("id"): a.get("optimized_cost_estimated", 0.0) for a in original_activations}
        budget_shifts, prioritized, deprioritized = [], [], []

        for opt_act in optimized_activations:
            act_id         = opt_act.get("id")
            original_cost  = original_costs.get(act_id, 0.0)
            optimized_cost = opt_act.get("optimized_cost_estimated", 0.0)
            if original_cost == 0:
                continue

            change_pct = (optimized_cost - original_cost) / original_cost
            if abs(change_pct) <= self.SHIFT_THRESHOLD:
                continue

            roi = (
                opt_act.get("estimated_reach", 0) * conversion_rates.get(act_id, 0.005) / optimized_cost
                if optimized_cost > 0 else 0
            )
            budget_shifts.append({
                "activation_id": act_id, "original_budget": original_cost,
                "optimized_budget": optimized_cost, "change_pct": change_pct * 100,
            })
            entry = {
                "activation_id":   act_id,
                "activation_name": f"{opt_act.get('sub_channel')} {opt_act.get('geography')} {opt_act.get('phase')}",
                "original_budget": original_cost, "optimized_budget": optimized_cost,
                "roi_per_dollar":  roi,
            }
            if change_pct > 0:
                entry["budget_increase_pct"] = change_pct * 100
                entry["reason"] = f"High ROI channel ({roi:.2f}x) — increased budget for maximum {opt_act.get('phase', '')} impact"
                prioritized.append(entry)
            else:
                entry["budget_decrease_pct"] = abs(change_pct) * 100
                entry["reason"] = f"Lower ROI ({roi:.2f}x) — budget reallocated to higher-performing channels"
                deprioritized.append(entry)

        total_increase = sum(a["optimized_budget"] - a["original_budget"] for a in prioritized)
        total_decrease = sum(a["original_budget"] - a["optimized_budget"] for a in deprioritized)

        return {
            "executive_summary": executive_summary,
            "summary": f"Budget optimised: +{budget_envelope_currency(original_activations)}{total_increase:,.0f} to high-ROI channels, -{budget_envelope_currency(original_activations)}{total_decrease:,.0f} from low-ROI channels",
            "budget_shifts":             budget_shifts,
            "prioritized_activations":   prioritized,
            "deprioritized_activations": deprioritized,
            "constraints_maintained": {
                "scheduled_dates": "All activation dates locked ✓",
                "channels":        "All channels preserved from Media Planner ✓",
                "geographies":     "All geographies preserved from Media Planner ✓",
            },
        }


def budget_envelope_currency(activations: list[dict]) -> str:
    return "$"


# ── Orchestrator ──────────────────────────────────────────────────────────────

async def budget_optimizer_agent(
    activations: list[dict[str, Any]],
    budget_envelope: dict[str, Any],
    campaign_context: dict[str, Any],
) -> dict[str, Any]:
    """
    Orchestrates all Budget Optimizer components with LLM-driven intelligence.

    Steps:
        1. LLM intelligence  — context-aware phase weights, channel priorities, narrative
        2. ConversionRateEstimator — channel-adjusted conversion rates
        3. BudgetOptimizer   — ROI-proportional allocation with channel priority
        4. ROIAnalyzer       — cross-phase/channel ROI metrics
        5. OptimizationReporter — shift report with mandate-specific executive summary

    Args:
        activations: List of activations from Media Planner
        budget_envelope: Dict with total_budget and currency
        campaign_context: Dict with campaign name, objective, description, target_audience, tone_board

    Returns:
        Dict with optimized_activations, roi_analysis, optimization_report,
        validation_errors, status
    """
    validation_errors = []

    try:
        # ── Step 0: LLM intelligence ──────────────────────────────────────────
        intelligence = await _generate_optimization_intelligence(
            activations, budget_envelope, campaign_context
        )

        phase_weights               = intelligence.get("phase_weights", {"Awareness": 1.0, "Engagement": 1.0, "Conversion": 1.0})
        channel_priorities          = intelligence.get("channel_priorities", [])
        conv_adjustments            = intelligence.get("audience_conversion_adjustments", {})
        executive_summary           = intelligence.get("executive_summary", "")

        # Normalise phase weights → proportional budget split
        total_weight = sum(phase_weights.values()) or 1.0
        total_budget = budget_envelope.get("total_budget", 0.0)
        phase_budgets = {phase: total_budget * (w / total_weight) for phase, w in phase_weights.items()}

        # ── Step 1: Stamp original costs ──────────────────────────────────────
        for act in activations:
            act["original_cost_estimated"]  = act.get("cost_estimated", 0.0)
            act["optimized_cost_estimated"] = act.get("cost_estimated", 0.0)

        # ── Step 2: Estimate conversion rates ─────────────────────────────────
        estimator = ConversionRateEstimator()
        conversion_rates = {}
        for act in activations:
            act_id     = act.get("id")
            ch_adjust  = conv_adjustments.get(act.get("sub_channel", ""), 1.0)
            conv_rates = estimator.estimate_conversion_rate(act, campaign_context, channel_adjustment=ch_adjust)
            conversion_rates[act_id] = conv_rates

        # ── Step 3: Optimise budget ────────────────────────────────────────────
        optimizer = BudgetOptimizer()
        optimized_activations = optimizer.optimize(
            activations, conversion_rates, phase_budgets, channel_priorities
        )

        # ── Step 4: Analyse ROI ────────────────────────────────────────────────
        analyzer     = ROIAnalyzer()
        roi_analysis = analyzer.analyze(optimized_activations, conversion_rates)

        # ── Step 5: Generate report ────────────────────────────────────────────
        reporter            = OptimizationReporter()
        optimization_report = reporter.generate_report(
            activations, optimized_activations, conversion_rates, executive_summary
        )

        # ── Step 6: Build output activations ─────────────────────────────────
        output_activations = []
        for opt_act in optimized_activations:
            act_id  = opt_act.get("id")
            conv    = conversion_rates.get(act_id, 0.005)
            reach   = opt_act.get("estimated_reach", 0)
            cost    = opt_act.get("optimized_cost_estimated", 1.0) or 1.0
            rw_conv = int(reach * conv)
            roi_per_dollar = rw_conv / cost

            original_cost = opt_act.get("original_cost_estimated", cost)
            if original_cost > 0:
                change_pct = (cost - original_cost) / original_cost
            else:
                change_pct = 0.0

            if abs(change_pct) <= 0.05:
                action = "unchanged"
                reason = "Within 5% threshold — no significant shift"
            elif change_pct > 0.05:
                action = "prioritized"
                reason = f"Increased {change_pct*100:.1f}% — {opt_act.get('sub_channel')} is high priority for {campaign_context.get('objective', 'this campaign')}"
            else:
                action = "deprioritized"
                reason = f"Decreased {abs(change_pct)*100:.1f}% — budget reallocated to higher-priority channels"

            output_activations.append({
                "id":                        act_id,
                "channel_enum":              opt_act.get("channel_enum"),
                "sub_channel":               opt_act.get("sub_channel"),
                "format":                    opt_act.get("format"),
                "geography":                 opt_act.get("geography"),
                "placement":                 opt_act.get("placement"),
                "phase":                     opt_act.get("phase"),
                "scheduled_date":            opt_act.get("scheduled_date"),
                "duration":                  opt_act.get("duration"),
                "frequency":                 opt_act.get("frequency"),
                "audience_segment":          opt_act.get("audience_segment"),
                "estimated_reach":           reach,
                "estimated_cpm":             opt_act.get("estimated_cpm"),
                "original_cost_estimated":   original_cost,
                "optimized_cost_estimated":  cost,
                "message_version_ref":       opt_act.get("message_version_ref"),
                "lead_time_days":            opt_act.get("lead_time_days"),
                "offline_constraints":       opt_act.get("offline_constraints"),
                "conversion_rate_estimated": conv,
                "reach_weighted_conversions": rw_conv,
                "roi_per_dollar":            roi_per_dollar,
                "optimization_action":       action,
                "reason":                    reason,
            })

        status = "success" if not validation_errors else "partial"
        return {
            "optimized_activations": output_activations,
            "roi_analysis":          roi_analysis,
            "optimization_report":   optimization_report,
            "validation_errors":     validation_errors,
            "status":                status,
        }

    except Exception as e:
        logger.error(f"Budget optimizer orchestrator failed: {e}")
        return {
            "optimized_activations": [],
            "roi_analysis":          None,
            "optimization_report":   None,
            "validation_errors":     [str(e)],
            "status":                "failed",
        }
