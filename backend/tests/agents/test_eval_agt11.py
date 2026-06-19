"""Eval tests for AGT-11 Video Generator."""
import os
from unittest.mock import patch

import pytest

from backend.app.agents.video_generator import VideoGenerationBrief, VideoGeneratorAgent
from backend.tests.agents.conftest_evals import (
    PASS_THRESHOLD,
    ScoreCard,
    load_golden,
    score_completeness,
    score_format,
)

REQUIRED_OUTPUT_FIELDS = [
    "campaign_id", "generation_id", "tenant_id", "job_id",
    "model_used", "status", "script_format",
]
REQUIRED_TYPES = {
    "campaign_id": str,
    "generation_id": str,
    "tenant_id": str,
    "job_id": str,
    "model_used": str,
    "status": str,
    "script_format": str,
}
MANDATE_IDS = ["mandate_1", "mandate_2", "mandate_3"]


def _build_brief(golden: dict) -> VideoGenerationBrief:
    mandate = golden["input_mandate"]
    concept = mandate.get("campaign_concept", {})
    return VideoGenerationBrief(
        campaign_id="eval-camp-agt11",
        tenant_id="eval-tenant-001",
        prompt=(
            f"Cinematic brand campaign, {concept.get('target_audience', 'urban professionals')}, "
            "golden hour, 4K, premium lifestyle, aspirational"
        ),
        script_text=(
            f"OPEN ON: City skyline at dawn. "
            f"NARRATOR: {concept.get('name', 'Our brand')} — redefining what's possible. "
            f"CUT TO: Product reveal. SUPER: Learn More."
        ),
        duration_seconds=15,
        script_format="social_video",
        campaign_theme=concept.get("description", "Brand innovation"),
        concept_name=concept.get("name", "Campaign"),
    )


@pytest.mark.parametrize("mandate_id", MANDATE_IDS)
@pytest.mark.asyncio
async def test_agt11_eval(mandate_id, eval_results, mock_agent_llm):
    """AGT-11 scores completeness + format >= 80 on each golden mandate."""
    golden = load_golden(mandate_id)
    brief = _build_brief(golden)

    with patch.dict(os.environ, {"NTM_STUB_EXTERNAL": "1"}):
        result = await VideoGeneratorAgent().generate(brief)

    output = result.model_dump(mode="json")

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
