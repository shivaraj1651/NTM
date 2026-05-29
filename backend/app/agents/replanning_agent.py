"""ReplanningAgent (AGT-14) — weekly activation replanning agent.

Reads AGT-13 AnalyticsSummary, identifies the top 3 underperforming (Red/Amber)
and top 3 overperforming (Green, score > +10%) activations, and generates
ReplanRecommendation records pending AGT-6 human approval.

Does NOT implement any changes — output is read-only recommendations.

TASK-021
"""

import json
import logging
from typing import Any, Dict, List, Tuple
from backend.app.external.stubs import stub_enabled

logger = logging.getLogger(__name__)

_FALLBACK_RATIONALE = "See KPI context"
_FALLBACK_IMPACT = "Impact not estimated"
_OVERPERFORM_THRESHOLD = 10.0


class ActivationScorer:
    """Scores activations by worst (minimum) KPI achievement_percent."""

    def score(self, analytics_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Attach a 'score' field (min achievement_percent) to each activation.

        Args:
            analytics_summary: Output dict from AGT-13 AnalyticsAgent.

        Returns:
            List of activation dicts each carrying 'score' and 'worst_kpi_name'.
        """
        scored = []
        for act in analytics_summary.get("activations", []):
            kpi_results = act.get("kpi_results", [])
            if not kpi_results:
                logger.warning(
                    "Activation %s has no kpi_results — skipped", act.get("activation_id")
                )
                continue
            worst = min(kpi_results, key=lambda k: k["achievement_percent"])
            entry = dict(act)
            entry["score"] = worst["achievement_percent"]
            entry["worst_kpi_name"] = worst["kpi_name"]
            scored.append(entry)
        return scored

    def get_underperformers(self, scored: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Return top 3 Red/Amber activations sorted by worst score ascending."""
        candidates = [a for a in scored if a["status"] in ("red", "amber")]
        return sorted(candidates, key=lambda a: a["score"])[:3]

    def get_overperformers(self, scored: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Return top 3 Green activations with score > +10%, sorted descending."""
        candidates = [
            a for a in scored
            if a["status"] == "green" and a["score"] > _OVERPERFORM_THRESHOLD
        ]
        return sorted(candidates, key=lambda a: a["score"], reverse=True)[:3]


class RecommendationMapper:
    """Maps (direction, worst_kpi_name, score) → (recommendation_type, estimated_cost_change_pct)."""

    _CREATIVE_KPIS = frozenset({"ctr", "conversion_rate"})
    _SPEND_KPIS = frozenset({"spend", "cpc", "cpm"})

    def map_type(
        self,
        direction: str,
        worst_kpi_name: str,
        score: float,
    ) -> Tuple[str, float]:
        """Return (recommendation_type, cost_change_pct).

        cost_change_pct is a percentage float:
          -100.0 = full pause, +20.0 = 20% spend increase, 0.0 = no cost change.

        Args:
            direction: 'underperforming' or 'overperforming'.
            worst_kpi_name: Name of the KPI with the worst achievement_percent.
            score: The worst KPI achievement_percent for this activation.
        """
        if direction == "underperforming":
            if score < -40.0:
                return "pause", -100.0
            if score < -20.0:
                if worst_kpi_name in self._CREATIVE_KPIS:
                    return "swap_creative", 5.0
                if worst_kpi_name in self._SPEND_KPIS:
                    return "increase_budget", 20.0
                return "swap_creative", 5.0
            return "adjust_targeting", 0.0

        # overperforming
        if score > 30.0:
            return "extend_duration", 15.0
        return "add_activation", 25.0


class LLMEnricher:
    """Fires one Anthropic call to fill rationale + expected_impact for all candidates."""

    _MODEL = "claude-sonnet-4-20250514"
    _MAX_TOKENS = 1024
    _SYSTEM = (
        "You are a media campaign performance analyst. "
        "Given a list of activation KPI summaries, return a JSON array. "
        "Each element must have exactly three keys: "
        "\"activation_id\" (string), "
        "\"rationale\" (1-2 sentences explaining the issue or opportunity), "
        "and \"expected_impact\" (1 sentence with a metric estimate where possible). "
        "Return ONLY the JSON array, no other text."
    )

    def __init__(self, anthropic_client: Any):
        self.client = anthropic_client

    async def enrich(
        self,
        candidates: List[Dict[str, Any]],
        activation_plan: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Enrich candidates with rationale and expected_impact via one LLM call.

        Falls back to safe placeholder strings if the LLM call fails or returns
        unparseable JSON. Never raises — soft failure only.

        Args:
            candidates: Partial ReplanRecommendation dicts (rationale/impact empty).
            activation_plan: Current activation plan passed as context to the LLM.

        Returns:
            Candidates with 'rationale' and 'expected_impact' filled.
        """
        payload = [
            {
                "activation_id": c["activation_id"],
                "recommendation_type": c["recommendation_type"],
                "direction": c.get("direction", ""),
                "kpi_context": c["kpi_context"],
            }
            for c in candidates
        ]
        user_message = (
            f"Activation plan context: {json.dumps(activation_plan)}\n\n"
            f"Candidates requiring recommendations:\n{json.dumps(payload, indent=2)}"
        )

        # NTM_STUB_EXTERNAL: stubbed external call
        if stub_enabled():
            logger.info("Replanning agent LLM enrichment stubbed (NTM_STUB_EXTERNAL)")
            result = []
            for candidate in candidates:
                enriched = dict(candidate)
                enriched["rationale"] = _FALLBACK_RATIONALE
                enriched["expected_impact"] = _FALLBACK_IMPACT
                result.append(enriched)
            return result

        enriched_index: Dict[str, Dict[str, str]] = {}
        try:
            response = await self.client.messages.create(
                model=self._MODEL,
                max_tokens=self._MAX_TOKENS,
                system=self._SYSTEM,
                messages=[{"role": "user", "content": user_message}],
            )
            raw = response.content[0].text
            parsed: List[Dict[str, Any]] = json.loads(raw)
            enriched_index = {item["activation_id"]: item for item in parsed}
        except Exception as exc:
            logger.warning("LLM enrichment failed (%s) — applying fallback strings", exc)

        result = []
        for candidate in candidates:
            enriched = dict(candidate)
            llm_data = enriched_index.get(candidate["activation_id"], {})
            enriched["rationale"] = llm_data.get("rationale", _FALLBACK_RATIONALE)
            enriched["expected_impact"] = llm_data.get("expected_impact", _FALLBACK_IMPACT)
            result.append(enriched)
        return result


class ReplanningAgent:
    """AGT-14 — weekly replanning agent.

    Identifies top 3 under/overperforming activations from AGT-13 AnalyticsSummary
    and generates ReplanRecommendation records pending AGT-6 approval.
    Output is read-only — no DB writes, no plan mutations.
    """

    def __init__(self, anthropic_client: Any):
        self.scorer = ActivationScorer()
        self.mapper = RecommendationMapper()
        self.enricher = LLMEnricher(anthropic_client)

    async def run_weekly_replan(
        self,
        mandate_id: str,
        analytics_summary: Dict[str, Any],
        activation_plan: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generate ReplanRecommendation list for a mandate.

        Args:
            mandate_id: Mandate identifier.
            analytics_summary: Output dict from AGT-13 AnalyticsAgent.run_daily_analysis().
            activation_plan: Current activation plan dict (context for LLM cost estimates).

        Returns:
            List of ReplanRecommendation dicts, each with status='pending_approval'.
            Returns [] if no activations exist in the summary.
        """
        if not analytics_summary.get("activations"):
            return []

        scored = self.scorer.score(analytics_summary)
        underperformers = self.scorer.get_underperformers(scored)
        overperformers = self.scorer.get_overperformers(scored)

        candidates: List[Dict[str, Any]] = []

        for act in underperformers:
            rec_type, cost_change = self.mapper.map_type(
                "underperforming", act["worst_kpi_name"], act["score"]
            )
            candidates.append(
                self._build_candidate(mandate_id, act, "underperforming", rec_type, cost_change)
            )

        for act in overperformers:
            rec_type, cost_change = self.mapper.map_type(
                "overperforming", act["worst_kpi_name"], act["score"]
            )
            candidates.append(
                self._build_candidate(mandate_id, act, "overperforming", rec_type, cost_change)
            )

        if not candidates:
            return []

        return await self.enricher.enrich(candidates, activation_plan)

    @staticmethod
    def _build_candidate(
        mandate_id: str,
        activation: Dict[str, Any],
        direction: str,
        rec_type: str,
        cost_change: float,
    ) -> Dict[str, Any]:
        return {
            "mandate_id": mandate_id,
            "activation_id": activation["activation_id"],
            "channel": activation.get("channel", ""),
            "direction": direction,
            "recommendation_type": rec_type,
            "rationale": "",
            "expected_impact": "",
            "estimated_cost_change": cost_change,
            "kpi_context": activation.get("kpi_results", []),
            "status": "pending_approval",
        }
