"""Eval tests for AGT-14 Replanning Agent."""
import os
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from backend.app.agents.replanning_agent import ReplanningAgent
from backend.tests.agents.conftest_evals import (
    PASS_THRESHOLD,
    ScoreCard,
    load_golden,
    score_completeness,
    score_format,
)

REQUIRED_OUTPUT_FIELDS = ["recommendations", "mandate_id"]
REQUIRED_TYPES = {
    "recommendations": list,
    "mandate_id": str,
}
MANDATE_IDS = ["mandate_1", "mandate_2", "mandate_3"]

# Analytics summary with activations to trigger the enrichment pipeline
_ANALYTICS_SUMMARY = {
    "date": "2026-06-19",
    "activations": [
        {
            "activation_id": "act-eval-001",
            "channel": "google_ads",
            "status": "red",
            "kpi_results": [
                {"kpi_name": "ctr", "target": 2.0, "actual": 0.8, "achievement_percent": -60.0}
            ],
        },
        {
            "activation_id": "act-eval-002",
            "channel": "meta_ads",
            "status": "green",
            "kpi_results": [
                {"kpi_name": "roas", "target": 3.0, "actual": 4.5, "achievement_percent": 50.0}
            ],
        },
    ],
    "red_alerts": ["act-eval-001"],
    "summary_by_channel": {"google_ads": {"total": 1, "red": 1}, "meta_ads": {"total": 1, "green": 1}},
}


@pytest.mark.parametrize("mandate_id", MANDATE_IDS)
@pytest.mark.asyncio
async def test_agt14_eval(mandate_id, eval_results, mock_agent_llm):
    """AGT-14 scores completeness + format >= 80 on each golden mandate."""
    load_golden(mandate_id)

    mandate_id_str = str(uuid4())
    mock_client = MagicMock()

    with patch.dict(os.environ, {"NTM_STUB_EXTERNAL": "1"}):
        agent = ReplanningAgent(mock_client)
        recommendations = await agent.run_weekly_replan(
            mandate_id=mandate_id_str,
            analytics_summary=_ANALYTICS_SUMMARY,
            activation_plan={"mandate_id": mandate_id_str, "activations": _ANALYTICS_SUMMARY["activations"]},
        )

    output = {"recommendations": recommendations, "mandate_id": mandate_id_str}

    completeness = score_completeness(output, REQUIRED_OUTPUT_FIELDS)
    fmt = score_format(output, REQUIRED_TYPES)

    card = ScoreCard(
        agent_id="AGT-14",
        agent_name="ReplanningAgent",
        mandate_id=mandate_id,
        completeness=completeness,
        format_score=fmt,
    )
    eval_results.append(card)

    assert card.overall >= PASS_THRESHOLD, (
        f"AGT-14 on {mandate_id}: overall={card.overall:.1f} "
        f"(completeness={completeness}, format={fmt})"
    )
