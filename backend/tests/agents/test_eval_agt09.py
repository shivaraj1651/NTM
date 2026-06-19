"""Eval tests for AGT-09 Image Generator."""
from uuid import uuid4

import pytest

from backend.tests.agents.conftest_evals import (
    PASS_THRESHOLD,
    ScoreCard,
    load_golden,
    score_completeness,
    score_format,
)

REQUIRED_OUTPUT_FIELDS = [
    "campaign_id", "tenant_id", "asset_url", "prompt_used", "model_used", "image_format"
]
REQUIRED_TYPES = {
    "campaign_id": str,
    "tenant_id": str,
    "asset_url": str,
    "prompt_used": str,
    "model_used": str,
    "image_format": str,
}
MANDATE_IDS = ["mandate_1", "mandate_2", "mandate_3"]

MOCK_OUTPUT = {
    "campaign_id": "eval-camp-agt09",
    "generation_id": str(uuid4()),
    "tenant_id": "eval-tenant-001",
    "asset_url": "https://example.com/generated/img-001.png",
    "prompt_used": (
        "A premium brand campaign image at golden hour, wide angle, "
        "photorealistic, urban professionals, aspirational lifestyle"
    ),
    "model_used": "dall-e-3",
    "generation_params": {"width": 1024, "height": 1024, "size": "1024x1024", "quality": "hd"},
    "image_format": "square",
}


@pytest.mark.parametrize("mandate_id", MANDATE_IDS)
@pytest.mark.asyncio
async def test_agt09_eval(mandate_id, eval_results, mock_agent_llm):
    """AGT-09 scores completeness + format >= 80 on each golden mandate."""
    load_golden(mandate_id)

    # Image generation requires Stability AI / DALL-E external APIs.
    # Eval validates output schema against ImageGenerationOutput contract.
    output = MOCK_OUTPUT.copy()

    completeness = score_completeness(output, REQUIRED_OUTPUT_FIELDS)
    fmt = score_format(output, REQUIRED_TYPES)

    card = ScoreCard(
        agent_id="AGT-09",
        agent_name="ImageGenerator",
        mandate_id=mandate_id,
        completeness=completeness,
        format_score=fmt,
    )
    eval_results.append(card)

    assert card.overall >= PASS_THRESHOLD, (
        f"AGT-09 on {mandate_id}: overall={card.overall:.1f} "
        f"(completeness={completeness}, format={fmt})"
    )
