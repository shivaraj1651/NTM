"""Eval tests for AGT-12 Digital Activator."""
import os
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from backend.app.agents.digital_activator import DigitalActivatorAgent
from backend.tests.agents.conftest_evals import (
    PASS_THRESHOLD,
    ScoreCard,
    load_golden,
    score_completeness,
    score_format,
)

REQUIRED_OUTPUT_FIELDS = ["status", "activation_id", "platforms", "subtask_count"]
REQUIRED_TYPES = {
    "status": str,
    "activation_id": str,
    "platforms": list,
    "subtask_count": int,
}
MANDATE_IDS = ["mandate_1", "mandate_2", "mandate_3"]


def _make_activation(channel: str = "google_ads") -> MagicMock:
    activation = MagicMock()
    activation.id = uuid4()
    activation.status = "approved"
    activation.channel_enum = channel
    return activation


def _make_db() -> AsyncMock:
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)
    return db


@pytest.mark.parametrize("mandate_id", MANDATE_IDS)
@pytest.mark.asyncio
async def test_agt12_eval(mandate_id, eval_results, mock_agent_llm):
    """AGT-12 scores completeness + format >= 80 on each golden mandate."""
    load_golden(mandate_id)

    activation = _make_activation("google_ads")
    mock_db = _make_db()

    with patch.dict(os.environ, {"NTM_STUB_EXTERNAL": "1"}):
        agent = DigitalActivatorAgent(mock_db)
        output = await agent.activate(
            activation,
            creative_url="https://example.com/creative.jpg",
            campaign_manager_email="manager@example.com",
        )

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
