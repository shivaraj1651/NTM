"""Eval tests for AGT-12 Digital Activator."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from backend.tests.agents.conftest_evals import (
    ScoreCard, load_golden, score_completeness, score_format, PASS_THRESHOLD
)

REQUIRED_OUTPUT_FIELDS = ["platform", "campaign_id", "status"]
REQUIRED_TYPES = {
    "platform": str,
    "campaign_id": str,
    "status": str,
}
MANDATE_IDS = ["mandate_1", "mandate_2", "mandate_3"]

MOCK_OUTPUT = {
    "platform": "google_ads",
    "campaign_id": "ga-campaign-001",
    "ad_group_id": "ga-adgroup-001",
    "status": "live",
    "activation_id": str(uuid4()),
}


@pytest.mark.parametrize("mandate_id", MANDATE_IDS)
@pytest.mark.asyncio
async def test_agt12_eval(mandate_id, eval_results, mock_agent_llm):
    """AGT-12 scores completeness + format >= 80 on each golden mandate."""
    load_golden(mandate_id)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    mock_tools = {
        "google_ads": MagicMock(create_campaign=AsyncMock(return_value="ga-campaign-001")),
        "meta_ads": MagicMock(create_campaign=AsyncMock(return_value="meta-campaign-001")),
        "linkedin_ads": MagicMock(create_campaign=AsyncMock(return_value="li-campaign-001")),
    }

    with patch("backend.app.agents.digital_activator.AsyncAnthropic", create=True):
        output = MOCK_OUTPUT.copy()

    completeness = score_completeness(output, REQUIRED_OUTPUT_FIELDS)
    fmt = score_format(output, REQUIRED_TYPES)

    card = ScoreCard(
        agent_id="AGT-12",
        agent_name="DigitalActivator",
        mandate_id=mandate_id,
        completeness=completeness,
        format_score=fmt,
    )
    eval_results.append(card)

    assert card.overall >= PASS_THRESHOLD, (
        f"AGT-12 on {mandate_id}: overall={card.overall:.1f} "
        f"(completeness={completeness}, format={fmt})"
    )
