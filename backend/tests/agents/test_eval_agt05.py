"""Eval tests for AGT-05 BudgetOptimizer."""
import pytest
from backend.app.agents.budget_optimizer import budget_optimizer_agent
from backend.tests.agents.conftest_evals import (
    ScoreCard, load_golden, score_completeness, score_format, PASS_THRESHOLD
)

MANDATE_IDS = ["mandate_1", "mandate_2", "mandate_3"]

REQUIRED_OUTPUT_FIELDS = [
    "optimized_activations", "roi_analysis", "optimization_report",
    "validation_errors", "status"
]
REQUIRED_OUTPUT_TYPES = {
    "optimized_activations": list,
    "roi_analysis": dict,
    "optimization_report": dict,
    "validation_errors": list,
    "status": str,
}

_SAMPLE_ACTIVATION = {
    "id": "act-001",
    "channel_enum": "Social",
    "sub_channel": "Instagram",
    "format": "Feed",
    "geography": "SG",
    "placement": "feed",
    "phase": "Awareness",
    "scheduled_date": "2026-06-01",
    "duration": 14,
    "frequency": "daily",
    "audience_segment": "Primary",
    "estimated_reach": 100000,
    "estimated_cpm": 5.0,
    "cost_estimated": 25000.0,
    "message_version_ref": "msg-v1",
    "lead_time_days": 7,
    "offline_constraints": None,
}


def _build_activations(budget: float) -> list:
    """Build minimal activation list for budget optimizer input."""
    act = dict(_SAMPLE_ACTIVATION)
    act["cost_estimated"] = budget * 0.5
    act2 = dict(_SAMPLE_ACTIVATION)
    act2["id"] = "act-002"
    act2["sub_channel"] = "TikTok"
    act2["cost_estimated"] = budget * 0.5
    return [act, act2]


@pytest.mark.parametrize("mandate_id", MANDATE_IDS)
@pytest.mark.asyncio
async def test_agt05_eval(mandate_id, eval_results):
    """AGT-05 scores completeness + format >= 80 on each golden mandate.

    No LLM mock needed — budget_optimizer_agent is a pure algorithmic agent.
    """
    golden = load_golden(mandate_id)
    mandate = golden["input_mandate"]
    budget = mandate["budget"]["total_amount"]

    activations = _build_activations(budget)
    budget_envelope = {"total_budget": budget, "currency": mandate["budget"]["currency"]}
    campaign_context = {
        "campaign_name": mandate["campaign_concept"]["name"],
        "tone_board": golden["golden_outputs"]["agt03_concept"]["tone_board"],
        "target_audience": mandate["campaign_concept"]["target_audience"],
    }

    output = await budget_optimizer_agent(activations, budget_envelope, campaign_context)

    completeness = score_completeness(output, REQUIRED_OUTPUT_FIELDS)
    fmt = score_format(output, REQUIRED_OUTPUT_TYPES)

    card = ScoreCard(
        agent_id="AGT-05",
        agent_name="BudgetOptimizer",
        mandate_id=mandate_id,
        completeness=completeness,
        format_score=fmt,
    )
    eval_results.append(card)

    assert card.overall >= PASS_THRESHOLD, (
        f"AGT-05 on {mandate_id}: overall={card.overall:.1f} "
        f"(completeness={completeness}, format={fmt})"
    )
