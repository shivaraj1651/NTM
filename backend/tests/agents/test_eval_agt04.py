"""Eval tests for AGT-04 MediaPlanner."""
import pytest

from backend.app.agents.media_planner import media_planner_agent
from backend.tests.agents.conftest_evals import (
    PASS_THRESHOLD,
    ScoreCard,
    load_golden,
    score_completeness,
    score_format,
)

MANDATE_IDS = ["mandate_1", "mandate_2", "mandate_3"]

REQUIRED_OUTPUT_FIELDS = ["activations", "budget_summary", "validation_errors", "allocation_log", "status"]
REQUIRED_OUTPUT_TYPES = {
    "activations": list,
    "validation_errors": list,
    "allocation_log": list,
    "status": str,
}


def _build_campaign_concept(golden: dict) -> dict:
    """Build a campaign_concept input from the golden agt03 output."""
    c = golden["golden_outputs"]["agt03_concept"]
    return {
        "channel_mix": [
            {"channel": ch["channel"], "weight": 1.0 / len(c["channel_mix"])}
            for ch in c["channel_mix"]
        ],
        "campaign_phasing": c["campaign_phasing"],
        "tone_board": c["tone_board"],
        "message_architecture": c["message_architecture"],
        "campaign_theme": c["campaign_theme"],
    }


@pytest.mark.parametrize("mandate_id", MANDATE_IDS)
@pytest.mark.asyncio
async def test_agt04_eval(mandate_id, eval_results):
    """AGT-04 scores completeness + format >= 80 on each golden mandate.

    No LLM mock needed — media_planner_agent is a pure algorithmic agent.
    """
    golden = load_golden(mandate_id)
    mandate = golden["input_mandate"]
    campaign_concept = _build_campaign_concept(golden)
    budget_envelope = {
        "total_budget": mandate["budget"]["total_amount"],
        "currency": mandate["budget"]["currency"],
        "contingency_pct": 0.10,
    }
    mandate_geography = mandate["geography"]

    output = await media_planner_agent(campaign_concept, budget_envelope, mandate_geography)

    # Normalize output: budget_summary might be a Pydantic model
    output_for_scoring = dict(output)
    if "budget_summary" in output_for_scoring and hasattr(output_for_scoring["budget_summary"], "model_dump"):
        output_for_scoring["budget_summary"] = output_for_scoring["budget_summary"].model_dump()

    completeness = score_completeness(output_for_scoring, REQUIRED_OUTPUT_FIELDS)
    fmt = score_format(output_for_scoring, REQUIRED_OUTPUT_TYPES)

    card = ScoreCard(
        agent_id="AGT-04",
        agent_name="MediaPlanner",
        mandate_id=mandate_id,
        completeness=completeness,
        format_score=fmt,
    )
    eval_results.append(card)

    assert card.overall >= PASS_THRESHOLD, (
        f"AGT-04 on {mandate_id}: overall={card.overall:.1f} "
        f"(completeness={completeness}, format={fmt})"
    )
