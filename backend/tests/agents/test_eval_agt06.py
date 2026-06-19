"""Eval tests for AGT-06 Creative Director."""
import os
from unittest.mock import MagicMock, patch

import pytest

from backend.app.agents.creative_director.models import (
    BrandGuidelines,
    CampaignInput,
    TargetAudience,
)
from backend.app.agents.creative_director_orchestrator import creative_director_agent
from backend.tests.agents.conftest_evals import (
    PASS_THRESHOLD,
    ScoreCard,
    load_golden,
    score_completeness,
    score_format,
)

REQUIRED_OUTPUT_FIELDS = ["campaign_id", "tenant_id", "platforms", "metadata"]
REQUIRED_TYPES = {
    "campaign_id": str,
    "tenant_id": str,
    "platforms": dict,
    "metadata": dict,
}
MANDATE_IDS = ["mandate_1", "mandate_2", "mandate_3"]


def _build_campaign_input(golden: dict) -> CampaignInput:
    mandate = golden["input_mandate"]
    concept = mandate.get("campaign_concept", {})
    return CampaignInput(
        campaign_id="eval-camp-agt06",
        tenant_id="eval-tenant-001",
        objectives=[concept.get("objective", "Increase brand awareness")],
        target_audience=TargetAudience(
            segments=[concept.get("target_audience", "General audience")]
        ),
        brand_guidelines=BrandGuidelines(
            tone="professional",
            colors=["#000000", "#FFFFFF"],
            messaging_rules=["Stay on-brand", "Be clear and concise"],
            mandatory_ctas=["Learn More"],
        ),
        platforms=["instagram"],
        product_details="Marketing Technology Platform",
        campaign_theme=concept.get("description", "Innovation drives growth"),
        primary_cta="Learn More",
    )


@pytest.mark.parametrize("mandate_id", MANDATE_IDS)
@pytest.mark.asyncio
async def test_agt06_eval(mandate_id, eval_results, mock_agent_llm):
    """AGT-06 scores completeness + format >= 80 on each golden mandate."""
    golden = load_golden(mandate_id)
    campaign_input = _build_campaign_input(golden)

    with patch(
        "backend.app.agents.creative_director.generator.AsyncAnthropic",
        return_value=MagicMock(),
    ):
        with patch.dict(os.environ, {"NTM_STUB_EXTERNAL": "1"}):
            result = await creative_director_agent(campaign_input)

    output = result.model_dump(mode="json")

    completeness = score_completeness(output, REQUIRED_OUTPUT_FIELDS)
    fmt = score_format(output, REQUIRED_TYPES)

    card = ScoreCard(
        agent_id="AGT-06",
        agent_name="CreativeDirector",
        mandate_id=mandate_id,
        completeness=completeness,
        format_score=fmt,
    )
    eval_results.append(card)

    assert card.overall >= PASS_THRESHOLD, (
        f"AGT-06 on {mandate_id}: overall={card.overall:.1f} "
        f"(completeness={completeness}, format={fmt})"
    )
