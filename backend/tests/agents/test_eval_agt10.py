"""Eval tests for AGT-10 Audio Generator."""
import os
from unittest.mock import patch

import pytest

from backend.app.agents.audio_generator import AudioGenerationBrief, AudioGeneratorAgent
from backend.tests.agents.conftest_evals import (
    PASS_THRESHOLD,
    ScoreCard,
    load_golden,
    score_completeness,
    score_format,
)

REQUIRED_OUTPUT_FIELDS = [
    "campaign_id", "generation_id", "tenant_id", "asset_url",
    "voice_id", "duration_seconds", "model_used", "script_format",
]
REQUIRED_TYPES = {
    "campaign_id": str,
    "generation_id": str,
    "tenant_id": str,
    "asset_url": str,
    "voice_id": str,
    "duration_seconds": (int, float),
    "model_used": str,
    "script_format": str,
}
MANDATE_IDS = ["mandate_1", "mandate_2", "mandate_3"]


def _build_brief(golden: dict) -> AudioGenerationBrief:
    mandate = golden["input_mandate"]
    concept = mandate.get("campaign_concept", {})
    return AudioGenerationBrief(
        campaign_id="eval-camp-agt10",
        tenant_id="eval-tenant-001",
        script_text=(
            f"Welcome to the future of marketing. "
            f"{concept.get('name', 'Our brand')} — where innovation meets impact. "
            f"Start your journey today."
        ),
        voice_style="warm",
        script_format="radio",
        campaign_theme=concept.get("description", "Brand innovation"),
    )


@pytest.mark.parametrize("mandate_id", MANDATE_IDS)
@pytest.mark.asyncio
async def test_agt10_eval(mandate_id, eval_results, mock_agent_llm):
    """AGT-10 scores completeness + format >= 80 on each golden mandate."""
    golden = load_golden(mandate_id)
    brief = _build_brief(golden)

    with patch.dict(os.environ, {"NTM_STUB_EXTERNAL": "1"}):
        result = await AudioGeneratorAgent().generate(brief)

    output = result.model_dump(mode="json")

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
