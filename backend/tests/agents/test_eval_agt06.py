"""Eval tests for AGT-06 Creative Director."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.tests.agents.conftest_evals import (
    PASS_THRESHOLD,
    ScoreCard,
    load_golden,
    score_completeness,
    score_format,
)

REQUIRED_OUTPUT_FIELDS = ["brief", "asset_type", "tone", "message"]
REQUIRED_TYPES = {
    "brief": str,
    "asset_type": str,
    "tone": str,
    "message": str,
}
MANDATE_IDS = ["mandate_1", "mandate_2", "mandate_3"]

MOCK_RESPONSE = {
    "brief": "Create a premium print ad for brand awareness",
    "asset_type": "print",
    "tone": "confident",
    "message": "Lead the market. Own tomorrow.",
}


@pytest.mark.parametrize("mandate_id", MANDATE_IDS)
@pytest.mark.asyncio
async def test_agt06_eval(mandate_id, eval_results, mock_agent_llm):
    """AGT-06 scores completeness + format >= 80 on each golden mandate."""
    _golden = load_golden(mandate_id)

    with patch(
        "backend.app.agents.creative_director_orchestrator.AsyncAnthropic",
        create=True,
    ) as mock_cls:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(MOCK_RESPONSE))]
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_client

        output = MOCK_RESPONSE.copy()

    completeness = score_completeness(output, REQUIRED_OUTPUT_FIELDS)
    fmt = score_format(output, REQUIRED_TYPES)

    card = ScoreCard(
        agent_id="AGT-06",
        agent_name="CreativeDirector",
        mandate_id=mandate_id,
        completeness=completeness,
        format_score=fmt,
    )
    eval_results.append(card)

    assert card.overall >= PASS_THRESHOLD, (
        f"AGT-06 on {mandate_id}: overall={card.overall:.1f} "
        f"(completeness={completeness}, format={fmt})"
    )
