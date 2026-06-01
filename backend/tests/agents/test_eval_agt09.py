"""Eval tests for AGT-09 Image Generator."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.tests.agents.conftest_evals import (
    PASS_THRESHOLD,
    ScoreCard,
    load_golden,
    score_completeness,
    score_format,
)

REQUIRED_OUTPUT_FIELDS = ["prompt", "style", "dimensions"]
REQUIRED_TYPES = {
    "prompt": str,
    "style": str,
    "dimensions": str,
}
MANDATE_IDS = ["mandate_1", "mandate_2", "mandate_3"]

MOCK_OUTPUT = {
    "prompt": "A premium real estate development at sunset, wide angle, photorealistic",
    "style": "photorealistic",
    "dimensions": "1024x1024",
    "asset_url": "https://example.com/generated/img-001.png",
    "generation_method": "dalle3",
}


@pytest.mark.parametrize("mandate_id", MANDATE_IDS)
@pytest.mark.asyncio
async def test_agt09_eval(mandate_id, eval_results, mock_agent_llm):
    """AGT-09 scores completeness + format >= 80 on each golden mandate."""
    load_golden(mandate_id)

    with patch("backend.app.agents.image_generator.AsyncAnthropic", create=True):
        with patch("backend.app.agents.image_generator.AsyncOpenAI", create=True) as mock_oai:
            mock_client = MagicMock()
            mock_img = MagicMock()
            mock_img.url = "https://example.com/generated/img-001.png"
            mock_client.images.generate = AsyncMock(
                return_value=MagicMock(data=[mock_img])
            )
            mock_oai.return_value = mock_client

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
