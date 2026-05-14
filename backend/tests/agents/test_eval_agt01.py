"""Eval tests for AGT-01 MandateAnalyst."""
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from backend.app.agents.mandate_analyst import mandate_analyst_agent
from backend.tests.agents.conftest_evals import (
    ScoreCard, load_golden, score_completeness, score_format, PASS_THRESHOLD
)

REQUIRED_OUTPUT_FIELDS = [
    "completeness_score", "missing_fields", "contradictions", "mandate_summary", "validated_at"
]
REQUIRED_TYPES = {
    "completeness_score": (int, float),
    "missing_fields": list,
    "contradictions": list,
    "mandate_summary": dict,
    "validated_at": str,
}
MANDATE_IDS = ["mandate_1", "mandate_2", "mandate_3"]


@pytest.mark.parametrize("mandate_id", MANDATE_IDS)
@pytest.mark.asyncio
async def test_agt01_eval(mandate_id, eval_results, mock_agent_llm):
    """AGT-01 scores completeness + format >= 80 on each golden mandate."""
    golden = load_golden(mandate_id)
    mandate = golden["input_mandate"]

    llm_response = {
        "contradictions": [],
        "mandate_summary": {
            "objective": mandate["campaign_concept"]["objective"],
            "budget_total": f"{mandate['budget']['total_amount']} {mandate['budget']['currency']}",
            "timeline": mandate["campaign_concept"]["timeline"],
            "key_risks": [],
            "readiness": "Ready to proceed"
        },
        "completeness_score": 95
    }

    with patch("backend.app.agents.mandate_analyst.AsyncAnthropic") as mock_cls:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(llm_response))]
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_client

        output = await mandate_analyst_agent(mandate)

    completeness = score_completeness(output, REQUIRED_OUTPUT_FIELDS)
    fmt = score_format(output, REQUIRED_TYPES)

    card = ScoreCard(
        agent_id="AGT-01",
        agent_name="MandateAnalyst",
        mandate_id=mandate_id,
        completeness=completeness,
        format_score=fmt,
    )
    eval_results.append(card)

    assert card.overall >= PASS_THRESHOLD, (
        f"AGT-01 on {mandate_id}: overall={card.overall:.1f} "
        f"(completeness={completeness}, format={fmt})"
    )
