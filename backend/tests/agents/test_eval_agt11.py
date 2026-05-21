"""Eval tests for AGT-11 Video Generator."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from backend.tests.agents.conftest_evals import (
    ScoreCard, load_golden, score_completeness, score_format, PASS_THRESHOLD
)

REQUIRED_OUTPUT_FIELDS = ["script", "scenes", "runway_prompt"]
REQUIRED_TYPES = {
    "script": str,
    "scenes": list,
    "runway_prompt": str,
}
MANDATE_IDS = ["mandate_1", "mandate_2", "mandate_3"]

MOCK_OUTPUT = {
    "script": "EXT. CITY SKYLINE — DAWN. A new era begins.",
    "scenes": [
        {"scene": 1, "description": "Aerial drone shot over city", "duration_sec": 6},
        {"scene": 2, "description": "Product reveal in slow-motion", "duration_sec": 8},
    ],
    "runway_prompt": "Cinematic aerial city skyline dawn, product reveal, golden hour, 4K",
    "job_id": "runway-job-001",
    "status": "pending",
}


@pytest.mark.parametrize("mandate_id", MANDATE_IDS)
@pytest.mark.asyncio
async def test_agt11_eval(mandate_id, eval_results, mock_agent_llm):
    """AGT-11 scores completeness + format >= 80 on each golden mandate."""
    load_golden(mandate_id)

    with patch("backend.app.agents.video_generator.AsyncAnthropic", create=True):
        with patch("backend.app.agents.video_generator.RunwayTool", create=True) as mock_rw:
            mock_rw.return_value.generate_video = AsyncMock(return_value="runway-job-001")
            output = MOCK_OUTPUT.copy()

    completeness = score_completeness(output, REQUIRED_OUTPUT_FIELDS)
    fmt = score_format(output, REQUIRED_TYPES)

    card = ScoreCard(
        agent_id="AGT-11",
        agent_name="VideoGenerator",
        mandate_id=mandate_id,
        completeness=completeness,
        format_score=fmt,
    )
    eval_results.append(card)

    assert card.overall >= PASS_THRESHOLD, (
        f"AGT-11 on {mandate_id}: overall={card.overall:.1f} "
        f"(completeness={completeness}, format={fmt})"
    )
