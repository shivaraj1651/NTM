"""Eval tests for AGT-02 CompetitiveIntel."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.agents.competitive_intel import identify_competitors_sync
from backend.tests.agents.conftest_evals import (
    PASS_THRESHOLD,
    ScoreCard,
    load_golden,
)

MANDATE_IDS = ["mandate_1", "mandate_2", "mandate_3"]
MIN_COMPETITORS = 5


def _score_completeness_agt02(competitors) -> float:
    """Score: enough competitors returned + all have name and confidence."""
    if not competitors or len(competitors) < MIN_COMPETITORS:
        return 0.0
    valid = sum(
        1 for c in competitors
        if hasattr(c, "name") and c.name
        and hasattr(c, "confidence") and isinstance(c.confidence, int)
    )
    return round(valid / len(competitors) * 100, 1)


def _score_format_agt02(competitors) -> float:
    """Binary: all items have name (str) and confidence (int 0-100)."""
    if not competitors:
        return 0.0
    for c in competitors:
        if not hasattr(c, "name") or not isinstance(c.name, str):
            return 0.0
        if not hasattr(c, "confidence") or not isinstance(c.confidence, int):
            return 0.0
        if not (0 <= c.confidence <= 100):
            return 0.0
    return 100.0


@pytest.mark.parametrize("mandate_id", MANDATE_IDS)
@pytest.mark.asyncio
async def test_agt02_eval(mandate_id, eval_results, mock_agent_llm):
    """AGT-02 scores completeness + format >= 80 on each golden mandate."""
    golden = load_golden(mandate_id)
    mandate = golden["input_mandate"]
    client_profile = {"industry": "consumer_goods", "existing_competitors": []}

    golden_competitors = golden["golden_outputs"]["agt02_competitors"]
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps({"competitors": golden_competitors}))]

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with patch(
        "backend.app.agents.competitive_intel.AsyncAnthropic",
        return_value=mock_client,
    ):
        competitors = await identify_competitors_sync(mandate, client_profile)

    completeness = _score_completeness_agt02(competitors)
    fmt = _score_format_agt02(competitors)

    card = ScoreCard(
        agent_id="AGT-02",
        agent_name="CompetitiveIntel",
        mandate_id=mandate_id,
        completeness=completeness,
        format_score=fmt,
    )
    eval_results.append(card)

    assert card.overall >= PASS_THRESHOLD, (
        f"AGT-02 on {mandate_id}: overall={card.overall:.1f} "
        f"(completeness={completeness}, format={fmt})"
    )
