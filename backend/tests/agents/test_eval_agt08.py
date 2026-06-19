"""Eval tests for AGT-08 Scriptwriter."""
import os
from unittest.mock import MagicMock, patch

import pytest

from backend.app.agents.scriptwriter import ScriptwriterAgent, ScriptwriterBrief
from backend.tests.agents.conftest_evals import (
    PASS_THRESHOLD,
    ScoreCard,
    load_golden,
    score_completeness,
    score_format,
)

REQUIRED_OUTPUT_FIELDS = ["campaign_id", "tenant_id", "script_format", "generation_id"]
REQUIRED_TYPES = {
    "campaign_id": str,
    "tenant_id": str,
    "script_format": str,
    "generation_id": str,
}
MANDATE_IDS = ["mandate_1", "mandate_2", "mandate_3"]


def _build_brief(golden: dict) -> ScriptwriterBrief:
    mandate = golden["input_mandate"]
    concept = mandate.get("campaign_concept", {})
    return ScriptwriterBrief(
        campaign_id="eval-camp-agt08",
        tenant_id="eval-tenant-001",
        script_format="tvc",
        core_concept=concept.get("name", "Brand Innovation"),
        campaign_theme=concept.get("description", "Technology leadership"),
        tone_adjectives=["bold", "cinematic", "inspiring"],
        visual_direction="Wide cinematic shots, golden hour lighting",
        brand_voice="Professional and aspirational",
        target_audience=concept.get("target_audience", "Urban professionals 18-45"),
        product_details="Marketing Technology Platform",
        primary_cta="Learn More",
        messaging_rules=["Show impact not features", "End on an emotional high"],
    )


@pytest.mark.parametrize("mandate_id", MANDATE_IDS)
@pytest.mark.asyncio
async def test_agt08_eval(mandate_id, eval_results, mock_agent_llm):
    """AGT-08 scores completeness + format >= 80 on each golden mandate."""
    golden = load_golden(mandate_id)
    brief = _build_brief(golden)

    with patch(
        "backend.app.agents.scriptwriter.AsyncAnthropic",
        return_value=MagicMock(),
    ):
        with patch.dict(os.environ, {"NTM_STUB_EXTERNAL": "1"}):
            result = await ScriptwriterAgent().generate(brief)

    output = result.model_dump(mode="json")

    completeness = score_completeness(output, REQUIRED_OUTPUT_FIELDS)
    fmt = score_format(output, REQUIRED_TYPES)

    card = ScoreCard(
        agent_id="AGT-08",
        agent_name="Scriptwriter",
        mandate_id=mandate_id,
        completeness=completeness,
        format_score=fmt,
    )
    eval_results.append(card)

    assert card.overall >= PASS_THRESHOLD, (
        f"AGT-08 on {mandate_id}: overall={card.overall:.1f} "
        f"(completeness={completeness}, format={fmt})"
    )
