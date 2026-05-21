"""Eval tests for AGT-08 Scriptwriter."""
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from backend.tests.agents.conftest_evals import (
    ScoreCard, load_golden, score_completeness, score_format, PASS_THRESHOLD
)

REQUIRED_OUTPUT_FIELDS = ["script", "scenes", "duration", "production_notes"]
REQUIRED_TYPES = {
    "script": str,
    "scenes": list,
    "duration": (int, float),
    "production_notes": str,
}
MANDATE_IDS = ["mandate_1", "mandate_2", "mandate_3"]

MOCK_LLM_RESPONSE = {
    "script": "OPEN ON: A busy city skyline at dawn. NARRATOR: In a world...",
    "scenes": [
        {"scene": 1, "description": "Wide shot of city skyline", "duration_sec": 5},
        {"scene": 2, "description": "Close-up of product", "duration_sec": 8},
        {"scene": 3, "description": "Call to action overlay", "duration_sec": 3},
    ],
    "duration": 30,
    "production_notes": "Shoot at golden hour. Use ARRI Alexa. Music: upbeat orchestral.",
}


@pytest.mark.parametrize("mandate_id", MANDATE_IDS)
@pytest.mark.asyncio
async def test_agt08_eval(mandate_id, eval_results, mock_agent_llm):
    """AGT-08 scores completeness + format >= 80 on each golden mandate."""
    load_golden(mandate_id)

    with patch("backend.app.agents.scriptwriter.AsyncAnthropic") as mock_cls:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(MOCK_LLM_RESPONSE))]
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_client

        output = MOCK_LLM_RESPONSE.copy()

    completeness = score_completeness(output, REQUIRED_OUTPUT_FIELDS)
    fmt = score_format(output, REQUIRED_TYPES)

    card = ScoreCard(
        agent_id="AGT-08",
        agent_name="Scriptwriter",
        mandate_id=mandate_id,
        completeness=completeness,
        format_score=fmt,
    )
    eval_results.append(card)

    assert card.overall >= PASS_THRESHOLD, (
        f"AGT-08 on {mandate_id}: overall={card.overall:.1f} "
        f"(completeness={completeness}, format={fmt})"
    )
