"""Eval tests for AGT-07 Copywriter."""
import os
from unittest.mock import MagicMock, patch

import pytest

from backend.app.agents.copywriter import CopywriterAgent, CreativeBrief
from backend.tests.agents.conftest_evals import (
    PASS_THRESHOLD,
    ScoreCard,
    load_golden,
    score_completeness,
    score_format,
)

REQUIRED_OUTPUT_FIELDS = ["campaign_id", "generation_id", "tenant_id", "assets"]
REQUIRED_TYPES = {
    "campaign_id": str,
    "generation_id": str,
    "tenant_id": str,
    "assets": list,
}
MANDATE_IDS = ["mandate_1", "mandate_2", "mandate_3"]


def _build_brief(golden: dict) -> CreativeBrief:
    mandate = golden["input_mandate"]
    concept = mandate.get("campaign_concept", {})
    return CreativeBrief(
        campaign_id="eval-camp-agt07",
        tenant_id="eval-tenant-001",
        core_concept=concept.get("name", "Brand Innovation"),
        tone_adjectives=["bold", "authentic", "engaging"],
        visual_direction="Clean, modern, aspirational",
        brand_voice="Professional and benefit-led",
        campaign_theme=concept.get("description", "Technology leadership"),
        primary_cta="Learn More",
        target_audience=concept.get("target_audience", "Urban professionals 18-45"),
        product_details="Marketing Technology Platform",
        messaging_rules=["Stay on-brand", "Lead with benefits", "Use active voice"],
    )


@pytest.mark.parametrize("mandate_id", MANDATE_IDS)
@pytest.mark.asyncio
async def test_agt07_eval(mandate_id, eval_results, mock_agent_llm):
    """AGT-07 scores completeness + format >= 80 on each golden mandate."""
    golden = load_golden(mandate_id)
    brief = _build_brief(golden)

    with patch(
        "backend.app.agents.copywriter.AsyncAnthropic",
        return_value=MagicMock(),
    ):
        with patch.dict(os.environ, {"NTM_STUB_EXTERNAL": "1"}):
            result = await CopywriterAgent().generate(brief)

    output = result.model_dump(mode="json")

    completeness = score_completeness(output, REQUIRED_OUTPUT_FIELDS)
    fmt = score_format(output, REQUIRED_TYPES)

    card = ScoreCard(
        agent_id="AGT-07",
        agent_name="Copywriter",
        mandate_id=mandate_id,
        completeness=completeness,
        format_score=fmt,
    )
    eval_results.append(card)

    assert card.overall >= PASS_THRESHOLD, (
        f"AGT-07 on {mandate_id}: overall={card.overall:.1f} "
        f"(completeness={completeness}, format={fmt})"
    )
