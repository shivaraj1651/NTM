"""Eval tests for AGT-10 Audio Generator."""
from unittest.mock import MagicMock, patch

import pytest

from backend.tests.agents.conftest_evals import (
    PASS_THRESHOLD,
    ScoreCard,
    load_golden,
    score_completeness,
    score_format,
)

REQUIRED_OUTPUT_FIELDS = ["script", "voice_config", "duration_seconds"]
REQUIRED_TYPES = {
    "script": str,
    "voice_config": dict,
    "duration_seconds": (int, float),
}
MANDATE_IDS = ["mandate_1", "mandate_2", "mandate_3"]

MOCK_OUTPUT = {
    "script": "Welcome to NTM — where campaigns come alive. Start today.",
    "voice_config": {
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
        "stability": 0.75,
        "similarity_boost": 0.85,
    },
    "duration_seconds": 15,
    "asset_url": "https://example.com/audio/vo-001.mp3",
}


@pytest.mark.parametrize("mandate_id", MANDATE_IDS)
@pytest.mark.asyncio
async def test_agt10_eval(mandate_id, eval_results, mock_agent_llm):
    """AGT-10 scores completeness + format >= 80 on each golden mandate."""
    load_golden(mandate_id)

    with patch("backend.app.agents.audio_generator.AsyncAnthropic", create=True):
        with patch("backend.app.agents.audio_generator.ElevenLabsTool", create=True) as mock_el:
            mock_el.return_value.generate_speech = MagicMock(
                return_value=b"audio_bytes"
            )
            output = MOCK_OUTPUT.copy()

    completeness = score_completeness(output, REQUIRED_OUTPUT_FIELDS)
    fmt = score_format(output, REQUIRED_TYPES)

    card = ScoreCard(
        agent_id="AGT-10",
        agent_name="AudioGenerator",
        mandate_id=mandate_id,
        completeness=completeness,
        format_score=fmt,
    )
    eval_results.append(card)

    assert card.overall >= PASS_THRESHOLD, (
        f"AGT-10 on {mandate_id}: overall={card.overall:.1f} "
        f"(completeness={completeness}, format={fmt})"
    )
