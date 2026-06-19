"""Eval tests for AGT-15 Report Generator."""
from uuid import uuid4

import pytest

from backend.app.agents.report_generator import DailyDigestBuilder
from backend.tests.agents.conftest_evals import (
    PASS_THRESHOLD,
    ScoreCard,
    load_golden,
    score_completeness,
    score_format,
)

REQUIRED_OUTPUT_FIELDS = [
    "report_type", "mandate_id", "generated_at",
    "summary_by_channel", "activations", "red_alert_count",
]
REQUIRED_TYPES = {
    "report_type": str,
    "mandate_id": str,
    "generated_at": str,
    "summary_by_channel": dict,
    "activations": list,
    "red_alert_count": int,
}
MANDATE_IDS = ["mandate_1", "mandate_2", "mandate_3"]

_ANALYTICS_SUMMARY = {
    "date": "2026-06-19",
    "activations": [
        {
            "activation_id": "act-eval-001",
            "channel": "google_ads",
            "status": "green",
            "kpi_results": [
                {"kpi_name": "ctr", "target": 2.0, "actual": 2.4, "achievement_percent": 120.0}
            ],
        }
    ],
    "red_alerts": [],
    "summary_by_channel": {
        "google_ads": {"total": 1, "green": 1, "amber": 0, "red": 0}
    },
}


@pytest.mark.parametrize("mandate_id", MANDATE_IDS)
@pytest.mark.asyncio
async def test_agt15_eval(mandate_id, eval_results, mock_agent_llm):
    """AGT-15 scores completeness + format >= 80 on each golden mandate."""
    load_golden(mandate_id)

    mandate_id_str = str(uuid4())
    builder = DailyDigestBuilder()
    output = builder.build(mandate_id_str, _ANALYTICS_SUMMARY)

    completeness = score_completeness(output, REQUIRED_OUTPUT_FIELDS)
    fmt = score_format(output, REQUIRED_TYPES)

    card = ScoreCard(
        agent_id="AGT-15",
        agent_name="ReportGenerator",
        mandate_id=mandate_id,
        completeness=completeness,
        format_score=fmt,
    )
    eval_results.append(card)

    assert card.overall >= PASS_THRESHOLD, (
        f"AGT-15 on {mandate_id}: overall={card.overall:.1f} "
        f"(completeness={completeness}, format={fmt})"
    )
