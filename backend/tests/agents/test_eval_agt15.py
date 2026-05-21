"""Eval tests for AGT-15 Report Generator."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from backend.tests.agents.conftest_evals import (
    ScoreCard, load_golden, score_completeness, score_format, PASS_THRESHOLD
)

REQUIRED_OUTPUT_FIELDS = ["report_type", "mandate_id", "generated_at"]
REQUIRED_TYPES = {
    "report_type": str,
    "mandate_id": str,
    "generated_at": str,
}
MANDATE_IDS = ["mandate_1", "mandate_2", "mandate_3"]

MOCK_OUTPUT = {
    "report_type": "daily",
    "mandate_id": str(uuid4()),
    "date": "2026-05-21",
    "generated_at": "2026-05-21T06:00:00Z",
    "summary_by_channel": {
        "google_ads": {"total": 3, "green": 2, "amber": 1, "red": 0},
    },
    "activations": [
        {
            "activation_id": "act-001",
            "channel": "google_ads",
            "status": "green",
            "kpi_results": [{"kpi_name": "ctr", "achievement_percent": 112.0}],
        }
    ],
    "red_alert_count": 0,
}


@pytest.mark.parametrize("mandate_id", MANDATE_IDS)
@pytest.mark.asyncio
async def test_agt15_eval(mandate_id, eval_results, mock_agent_llm):
    """AGT-15 scores completeness + format >= 80 on each golden mandate."""
    load_golden(mandate_id)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))
    )

    with patch("backend.app.agents.report_generator.AsyncAnthropic", create=True):
        output = MOCK_OUTPUT.copy()

    completeness = score_completeness(output, REQUIRED_OUTPUT_FIELDS)
    fmt = score_format(output, REQUIRED_TYPES)

    card = ScoreCard(
        agent_id="AGT-15",
        agent_name="ReportGenerator",
        mandate_id=mandate_id,
        completeness=completeness,
        format_score=fmt,
    )
    eval_results.append(card)

    assert card.overall >= PASS_THRESHOLD, (
        f"AGT-15 on {mandate_id}: overall={card.overall:.1f} "
        f"(completeness={completeness}, format={fmt})"
    )
