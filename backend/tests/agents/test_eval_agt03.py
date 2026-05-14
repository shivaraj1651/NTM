"""Eval tests for AGT-03 CampaignStrategist (includes coherence scoring)."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.agents.campaign_strategist import campaign_strategist_agent
from backend.tests.agents.conftest_evals import (
    ScoreCard, load_golden, score_completeness, score_format,
    score_coherence, PASS_THRESHOLD
)

MANDATE_IDS = ["mandate_1", "mandate_2", "mandate_3"]

REQUIRED_OUTPUT_FIELDS = ["campaigns", "validation_errors", "regeneration_log"]
REQUIRED_OUTPUT_TYPES = {
    "campaigns": list,
    "validation_errors": list,
    "regeneration_log": list,
}
REQUIRED_CAMPAIGN_FIELDS = [
    "name", "tagline", "strategic_narrative", "campaign_theme",
    "audience_segmentation", "channel_mix", "message_architecture",
    "campaign_phasing", "tone_board", "mandate_fit_score", "gap_exploitation_score"
]


def _score_completeness_agt03(output: dict) -> float:
    """Score on top-level output keys + completeness of first campaign."""
    top_score = score_completeness(output, REQUIRED_OUTPUT_FIELDS)
    campaigns = output.get("campaigns", [])
    if not campaigns:
        return top_score * 0.3  # heavy penalty for no campaigns
    first = campaigns[0] if isinstance(campaigns[0], dict) else campaigns[0].model_dump()
    campaign_score = score_completeness(first, REQUIRED_CAMPAIGN_FIELDS)
    return round(0.3 * top_score + 0.7 * campaign_score, 1)


def _make_golden_campaign_json(golden_concept: dict) -> str:
    """Build a CampaignConcept JSON matching the Pydantic schema."""
    concept = {
        "name": golden_concept["name"],
        "tagline": golden_concept["tagline"],
        "strategic_narrative": golden_concept["strategic_narrative"],
        "campaign_theme": golden_concept["campaign_theme"],
        "audience_segmentation": golden_concept["audience_segmentation"],
        "channel_mix": [
            {
                "channel": c["channel"],
                "rationale": c["rationale"],
                "competitor_gap": c["competitor_gap"],
            }
            for c in golden_concept["channel_mix"]
        ],
        "message_architecture": golden_concept["message_architecture"],
        "campaign_phasing": golden_concept["campaign_phasing"],
        "tone_board": golden_concept["tone_board"],
        "risk_flags": {"legal": None, "regulatory": None, "sensitivity": None},
        "mandate_fit_score": golden_concept["mandate_fit_score"],
        "gap_exploitation_score": golden_concept["gap_exploitation_score"],
    }
    return json.dumps(concept)


@pytest.mark.parametrize("mandate_id", MANDATE_IDS)
@pytest.mark.asyncio
async def test_agt03_eval(mandate_id, eval_results):
    """AGT-03 scores completeness + format + coherence >= 80 on each golden mandate."""
    golden = load_golden(mandate_id)
    mandate = golden["input_mandate"]
    golden_concept = golden["golden_outputs"]["agt03_concept"]
    golden_competitors = golden["golden_outputs"]["agt02_competitors"]

    ci_report = {
        "competitors": golden_competitors,
        "whitespace_opportunities": {
            "untapped_channels": ["TikTok"],
            "messaging_gaps": ["authenticity"],
            "geographic_gaps": [],
        },
        "market_concentration": "fragmented",
    }

    campaign_json = _make_golden_campaign_json(golden_concept)

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=campaign_json)]
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with patch("backend.app.agents.campaign_strategist.AsyncAnthropic", return_value=mock_client):
        output = await campaign_strategist_agent(mandate, ci_report)

    # Normalize campaigns list to dicts
    campaigns = output.get("campaigns", [])
    campaigns_as_dicts = []
    for c in campaigns:
        if hasattr(c, "model_dump"):
            campaigns_as_dicts.append(c.model_dump())
        elif isinstance(c, dict):
            campaigns_as_dicts.append(c)
    output_for_scoring = {**output, "campaigns": campaigns_as_dicts}

    completeness = _score_completeness_agt03(output_for_scoring)
    fmt = score_format(output_for_scoring, REQUIRED_OUTPUT_TYPES)

    # Coherence: use mock client returning score 85
    coherence_mock = MagicMock()
    coherence_response = MagicMock()
    coherence_response.content = [MagicMock(text='{"score": 85}')]
    coherence_mock.messages.create = AsyncMock(return_value=coherence_response)
    coherence = await score_coherence(
        campaigns_as_dicts[0] if campaigns_as_dicts else {},
        golden_concept,
        coherence_mock,
    )

    card = ScoreCard(
        agent_id="AGT-03",
        agent_name="CampaignStrategist",
        mandate_id=mandate_id,
        completeness=completeness,
        format_score=fmt,
        coherence=coherence,
    )
    eval_results.append(card)

    assert card.overall >= PASS_THRESHOLD, (
        f"AGT-03 on {mandate_id}: overall={card.overall:.1f} "
        f"(completeness={completeness}, format={fmt}, coherence={coherence})"
    )
