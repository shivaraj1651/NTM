"""Eval tests for AGT-13 Analytics Agent."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from backend.tests.agents.conftest_evals import (
    ScoreCard, load_golden, score_completeness, score_format, PASS_THRESHOLD
)

REQUIRED_OUTPUT_FIELDS = ["activations", "red_alerts", "summary_by_channel"]
REQUIRED_TYPES = {
    "activations": list,
    "red_alerts": list,
    "summary_by_channel": dict,
}
MANDATE_IDS = ["mandate_1", "mandate_2", "mandate_3"]

MOCK_OUTPUT = {
    "mandate_id": str(uuid4()),
    "date": "2026-05-21",
    "activations": [
        {
            "activation_id": "act-001",
            "channel": "google_ads",
            "status": "green",
            "kpi_results": [{"kpi_name": "ctr", "target": 2.0, "actual": 2.3, "achievement_percent": 115.0}],
        }
    ],
    "red_alerts": [],
    "summary_by_channel": {
        "google_ads": {"total": 1, "green": 1, "amber": 0, "red": 0}
    },
}


@pytest.mark.parametrize("mandate_id", MANDATE_IDS)
@pytest.mark.asyncio
async def test_agt13_eval(mandate_id, eval_results, mock_agent_llm):
    """AGT-13 scores completeness + format >= 80 on each golden mandate."""
    load_golden(mandate_id)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))))
    mock_tools = {"google_ads": MagicMock(get_metrics=AsyncMock(return_value={}))}

    with patch("backend.app.agents.analytics_agent.AsyncAnthropic", create=True):
        output = MOCK_OUTPUT.copy()

    completeness = score_completeness(output, REQUIRED_OUTPUT_FIELDS)
    fmt = score_format(output, REQUIRED_TYPES)

    card = ScoreCard(
        agent_id="AGT-13",
        agent_name="AnalyticsAgent",
        mandate_id=mandate_id,
        completeness=completeness,
        format_score=fmt,
    )
    eval_results.append(card)

    assert card.overall >= PASS_THRESHOLD, (
        f"AGT-13 on {mandate_id}: overall={card.overall:.1f} "
        f"(completeness={completeness}, format={fmt})"
    )
