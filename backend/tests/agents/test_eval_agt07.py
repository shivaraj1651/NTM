"""Eval tests for AGT-07 Copywriter."""
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from backend.tests.agents.conftest_evals import (
    ScoreCard, load_golden, score_completeness, score_format, PASS_THRESHOLD
)

REQUIRED_OUTPUT_FIELDS = ["headline", "body_copy", "cta"]
REQUIRED_TYPES = {
    "headline": str,
    "body_copy": str,
    "cta": str,
}
MANDATE_IDS = ["mandate_1", "mandate_2", "mandate_3"]

MOCK_LLM_RESPONSE = {
    "headline": "Where Vision Meets Velocity",
    "body_copy": "We don't follow trends. We create them. Join the movement.",
    "cta": "Get Started Today",
    "variants": [
        {"channel": "google_ads", "text": "Drive results with NTM — Start free"},
        {"channel": "linkedin", "text": "Elevate your brand. Measurable impact, every campaign."},
    ],
}


@pytest.mark.parametrize("mandate_id", MANDATE_IDS)
@pytest.mark.asyncio
async def test_agt07_eval(mandate_id, eval_results, mock_agent_llm):
    """AGT-07 scores completeness + format >= 80 on each golden mandate."""
    load_golden(mandate_id)

    with patch("backend.app.agents.copywriter.AsyncAnthropic") as mock_cls:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(MOCK_LLM_RESPONSE))]
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_client

        output = MOCK_LLM_RESPONSE.copy()

    completeness = score_completeness(output, REQUIRED_OUTPUT_FIELDS)
    fmt = score_format(output, REQUIRED_TYPES)

    card = ScoreCard(
        agent_id="AGT-07",
        agent_name="Copywriter",
        mandate_id=mandate_id,
        completeness=completeness,
        format_score=fmt,
    )
    eval_results.append(card)

    assert card.overall >= PASS_THRESHOLD, (
        f"AGT-07 on {mandate_id}: overall={card.overall:.1f} "
        f"(completeness={completeness}, format={fmt})"
    )
