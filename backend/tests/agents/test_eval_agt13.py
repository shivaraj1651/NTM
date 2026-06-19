"""Eval tests for AGT-13 Analytics Agent."""
import os
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from backend.app.agents.analytics_agent import AnalyticsAgent
from backend.tests.agents.conftest_evals import (
    PASS_THRESHOLD,
    ScoreCard,
    load_golden,
    score_completeness,
    score_format,
)

REQUIRED_OUTPUT_FIELDS = [
    "mandate_id", "date", "activations", "red_alerts", "summary_by_channel"
]
REQUIRED_TYPES = {
    "mandate_id": str,
    "date": str,
    "activations": list,
    "red_alerts": list,
    "summary_by_channel": dict,
}
MANDATE_IDS = ["mandate_1", "mandate_2", "mandate_3"]


def _make_db() -> AsyncMock:
    db = AsyncMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    result = MagicMock()
    result.scalars.return_value = scalars_mock
    db.execute = AsyncMock(return_value=result)
    return db


@pytest.mark.parametrize("mandate_id", MANDATE_IDS)
@pytest.mark.asyncio
async def test_agt13_eval(mandate_id, eval_results, mock_agent_llm):
    """AGT-13 scores completeness + format >= 80 on each golden mandate."""
    load_golden(mandate_id)

    mock_db = _make_db()
    platform_tools: dict = {}
    mandate_uuid = uuid4()

    with patch.dict(os.environ, {"NTM_STUB_EXTERNAL": "1"}):
        agent = AnalyticsAgent(mock_db, platform_tools)
        output = await agent.run_daily_analysis(mandate_uuid)

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
