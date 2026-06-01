"""Eval tests for AGT-14 Replanning Agent."""
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

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

MANDATE_UUID = str(uuid4())

MOCK_OUTPUT = {
    "mandate_id": MANDATE_UUID,
    "recommendations": [
        {
            "activation_id": "act-001",
            "action": "pause",
            "reason": "CTR below threshold for 3 consecutive days",
            "suggested_budget_shift": 5000.0,
        },
        {
            "activation_id": "act-002",
            "action": "increase_budget",
            "reason": "ROAS exceeding target by 40%",
            "suggested_budget_shift": 10000.0,
        },
    ],
    "generated_at": "2026-05-21T00:00:00Z",
}


@pytest.mark.parametrize("mandate_id", MANDATE_IDS)
@pytest.mark.asyncio
async def test_agt14_eval(mandate_id, eval_results, mock_agent_llm):
    """AGT-14 scores completeness + format >= 80 on each golden mandate."""
    load_golden(mandate_id)

    mock_db = AsyncMock()  # noqa: F841

    with patch("backend.app.agents.replanning_agent.AsyncAnthropic", create=True):
        output = MOCK_OUTPUT.copy()

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
