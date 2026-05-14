"""Tests for ReplanningAgent (AGT-14) — TDD RED phase."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.app.agents.replanning_agent import (
    ActivationScorer,
    RecommendationMapper,
    LLMEnricher,
    ReplanningAgent,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _activation(act_id, status, kpi_results):
    return {
        "activation_id": act_id,
        "campaign_id": "campaign-001",
        "channel": "google_ads",
        "sub_channel": "Google Search",
        "status": status,
        "kpi_results": kpi_results,
        "metrics": {"impressions": 1000, "clicks": 50, "conversions": 2, "spend": 500.0},
    }


def _kpi(kpi_name, achievement_percent, status):
    return {
        "kpi_name": kpi_name,
        "target": 5.0,
        "actual": 3.0,
        "achievement_percent": achievement_percent,
        "threshold_unit": "percent",
        "status": status,
    }


def _summary(activations):
    return {
        "mandate_id": "mandate-001",
        "date": "2026-05-12",
        "activations": activations,
        "red_alerts": [],
        "summary_by_channel": {},
    }


def _mock_client(llm_json_response):
    client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text=json.dumps(llm_json_response))]
    client.messages.create = AsyncMock(return_value=mock_resp)
    return client


# ---------------------------------------------------------------------------
# ActivationScorer
# ---------------------------------------------------------------------------

class TestActivationScorer:
    def test_scorer_ranks_underperformers(self):
        """Red/Amber activations sorted worst-first, capped at 3; Green excluded."""
        scorer = ActivationScorer()
        activations = [
            _activation("act-1", "red",   [_kpi("ctr", -50.0, "red")]),
            _activation("act-2", "amber", [_kpi("ctr", -15.0, "amber")]),
            _activation("act-3", "red",   [_kpi("ctr", -30.0, "red")]),
            _activation("act-4", "red",   [_kpi("ctr", -45.0, "red")]),
            _activation("act-5", "green", [_kpi("ctr",  20.0, "green")]),
        ]
        scored = scorer.score(_summary(activations))
        under = scorer.get_underperformers(scored)

        assert len(under) == 3
        assert under[0]["activation_id"] == "act-1"   # -50 worst
        assert under[1]["activation_id"] == "act-4"   # -45
        assert under[2]["activation_id"] == "act-3"   # -30
        assert all(a["status"] in ("red", "amber") for a in under)

    def test_scorer_ranks_overperformers(self):
        """Green activations with score > +10 sorted best-first, capped at 3; others excluded."""
        scorer = ActivationScorer()
        activations = [
            _activation("act-1", "green", [_kpi("ctr", 35.0, "green")]),
            _activation("act-2", "green", [_kpi("ctr",  5.0, "green")]),  # below threshold
            _activation("act-3", "green", [_kpi("ctr", 15.0, "green")]),
            _activation("act-4", "green", [_kpi("ctr", 50.0, "green")]),
            _activation("act-5", "green", [_kpi("ctr", 25.0, "green")]),
            _activation("act-6", "red",   [_kpi("ctr", -30.0, "red")]),
        ]
        scored = scorer.score(_summary(activations))
        over = scorer.get_overperformers(scored)

        assert len(over) == 3
        assert over[0]["activation_id"] == "act-4"   # 50 best
        assert over[1]["activation_id"] == "act-1"   # 35
        assert over[2]["activation_id"] == "act-5"   # 25
        # act-2 (score 5) and act-6 (red) excluded


# ---------------------------------------------------------------------------
# RecommendationMapper
# ---------------------------------------------------------------------------

class TestRecommendationMapper:
    def test_mapper_pause_on_severe_miss(self):
        """achievement < -40% → pause, cost_change = -100.0."""
        mapper = RecommendationMapper()
        rec_type, cost_change = mapper.map_type("underperforming", "conversion_rate", -45.0)
        assert rec_type == "pause"
        assert cost_change == -100.0

    def test_mapper_swap_creative_on_ctr_miss(self):
        """CTR in -20% to -40% range → swap_creative, cost_change = +5.0."""
        mapper = RecommendationMapper()
        rec_type, cost_change = mapper.map_type("underperforming", "ctr", -30.0)
        assert rec_type == "swap_creative"
        assert cost_change == 5.0

    def test_mapper_extend_duration_on_overperform(self):
        """score > +30% overperforming → extend_duration, cost_change = +15.0."""
        mapper = RecommendationMapper()
        rec_type, cost_change = mapper.map_type("overperforming", "ctr", 35.0)
        assert rec_type == "extend_duration"
        assert cost_change == 15.0


# ---------------------------------------------------------------------------
# LLMEnricher
# ---------------------------------------------------------------------------

class TestLLMEnricher:
    @pytest.mark.asyncio
    async def test_enricher_parses_llm_response(self):
        """Valid LLM JSON → rationale and expected_impact populated on each candidate."""
        llm_payload = [
            {
                "activation_id": "act-1",
                "rationale": "CTR is 30% below target.",
                "expected_impact": "Expect +15% CTR after creative swap.",
            }
        ]
        client = _mock_client(llm_payload)
        enricher = LLMEnricher(client)
        candidates = [
            {"activation_id": "act-1", "recommendation_type": "swap_creative", "kpi_context": []}
        ]
        result = await enricher.enrich(candidates, {})

        assert result[0]["rationale"] == "CTR is 30% below target."
        assert result[0]["expected_impact"] == "Expect +15% CTR after creative swap."

    @pytest.mark.asyncio
    async def test_enricher_fallback_on_bad_json(self):
        """Malformed LLM response → fallback strings applied, no exception raised."""
        client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="not valid json {{")]
        client.messages.create = AsyncMock(return_value=mock_resp)

        enricher = LLMEnricher(client)
        candidates = [
            {"activation_id": "act-1", "recommendation_type": "pause", "kpi_context": []}
        ]
        result = await enricher.enrich(candidates, {})

        assert len(result) == 1
        assert result[0]["rationale"] == "See KPI context"
        assert result[0]["expected_impact"] == "Impact not estimated"


# ---------------------------------------------------------------------------
# ReplanningAgent — integration
# ---------------------------------------------------------------------------

class TestReplanningAgent:
    @pytest.mark.asyncio
    async def test_agent_full_run(self):
        """3 underperformers + 3 overperformers → 6 recommendations, all pending_approval."""
        activations = [
            _activation("under-1", "red",   [_kpi("ctr", -45.0, "red")]),
            _activation("under-2", "red",   [_kpi("conversion_rate", -35.0, "red")]),
            _activation("under-3", "amber", [_kpi("cpc", -15.0, "amber")]),
            _activation("over-1",  "green", [_kpi("ctr", 40.0, "green")]),
            _activation("over-2",  "green", [_kpi("ctr", 25.0, "green")]),
            _activation("over-3",  "green", [_kpi("ctr", 12.0, "green")]),
        ]
        ids = [a["activation_id"] for a in activations]
        llm_response = [
            {"activation_id": i, "rationale": "test rationale", "expected_impact": "test impact"}
            for i in ids
        ]
        agent = ReplanningAgent(_mock_client(llm_response))
        recs = await agent.run_weekly_replan("mandate-001", _summary(activations), {})

        assert len(recs) == 6
        assert all(r["status"] == "pending_approval" for r in recs)
        assert all("recommendation_type" in r for r in recs)
        assert all("rationale" in r for r in recs)
        assert all("estimated_cost_change" in r for r in recs)
        assert all("kpi_context" in r for r in recs)

    @pytest.mark.asyncio
    async def test_agent_empty_summary(self):
        """Empty activations list → returns [] without calling LLM."""
        client = MagicMock()
        client.messages.create = AsyncMock()
        agent = ReplanningAgent(client)
        result = await agent.run_weekly_replan("mandate-001", _summary([]), {})

        assert result == []
        client.messages.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_agent_fewer_than_three(self):
        """Only 1 qualifying underperformer → 1 recommendation returned (no padding)."""
        activations = [
            _activation("under-1", "red",   [_kpi("ctr", -50.0, "red")]),
            _activation("over-1",  "green", [_kpi("ctr",   5.0, "green")]),  # score ≤ 10, excluded
        ]
        llm_response = [
            {"activation_id": "under-1", "rationale": "Low CTR", "expected_impact": "+20% CTR"}
        ]
        agent = ReplanningAgent(_mock_client(llm_response))
        recs = await agent.run_weekly_replan("mandate-001", _summary(activations), {})

        assert len(recs) == 1
        assert recs[0]["activation_id"] == "under-1"
        assert recs[0]["direction"] == "underperforming"
