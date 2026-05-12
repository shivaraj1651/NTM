# AGT-14 Replanning Agent — Design Spec

**Date:** 2026-05-12  
**Task:** TASK-021  
**Branch:** feature/TASK-020 (continues on feature/TASK-021)  
**LLM:** claude-sonnet-4-20250514

---

## Overview

AGT-14 is a weekly scheduled agent that reads AGT-13's `AnalyticsSummary`, identifies the top 3 underperforming and top 3 overperforming activations, and generates specific `ReplanRecommendation` records pending AGT-6 human approval. It does **not** implement any changes.

---

## Files

| File | Purpose |
|---|---|
| `backend/app/agents/replanning_agent.py` | Agent implementation (sole module-scope file) |
| `backend/app/tasks/replanning_tasks.py` | Celery Beat weekly task wrapping the agent |
| `backend/tests/agents/test_replanning_agent.py` | Unit tests (10 tests, no DB required) |

---

## Architecture

### Classes

**`ActivationScorer`**  
Scores every activation entry from `AnalyticsSummary` by its worst KPI `achievement_percent`.

- `score(analytics_summary: dict) -> list[dict]` — returns scored activation list
- Score = `min(achievement_percent)` across all `kpi_results` for that activation
- Underperformers: activation `status` in `{"red", "amber"}`, sorted ascending, capped at 3
- Overperformers: activation `status == "green"` AND score > `+10.0`, sorted descending, capped at 3

**`RecommendationMapper`**  
Maps `(direction, worst_kpi_name, score)` → `recommendation_type` + `estimated_cost_change` via a deterministic rule table. Pure Python, no I/O.

**`LLMEnricher`**  
Fires one `AsyncAnthropic` call with all candidate activations (up to 6) batched in a single structured prompt. Fills `rationale` (1–2 sentences) and `expected_impact` (1 sentence with metric estimate where possible). Falls back to safe strings on parse failure.

**`ReplanningAgent`**  
Orchestrates the three components. Constructor accepts `anthropic_client: AsyncAnthropic`. Public entry point: `run_weekly_replan(mandate_id, analytics_summary, activation_plan)`.

---

## Data Contracts

### Input: `AnalyticsSummary` (dict from AGT-13)

```python
{
    "mandate_id": str,
    "date": str,
    "activations": [
        {
            "activation_id": str,
            "campaign_id": str,
            "channel": str,
            "sub_channel": str,
            "status": "red" | "amber" | "green",
            "kpi_results": [
                {
                    "kpi_name": str,
                    "target": float,
                    "actual": float,
                    "achievement_percent": float,
                    "threshold_unit": str,
                    "status": "red" | "amber" | "green"
                }
            ],
            "metrics": {"impressions": int, "clicks": int, "conversions": int, "spend": float}
        }
    ],
    "red_alerts": [...],
    "summary_by_channel": {...}
}
```

### Input: `activation_plan` (dict passthrough)

Accepted as-is. Passed to LLM enricher as context for cost estimation. No schema enforced.

### Output: `ReplanRecommendation` (dict)

```python
{
    "mandate_id": str,
    "activation_id": str,
    "channel": str,
    "direction": "underperforming" | "overperforming",
    "recommendation_type": "pause" | "increase_budget" | "swap_creative" |
                           "add_activation" | "adjust_targeting" | "extend_duration",
    "rationale": str,            # LLM-generated
    "expected_impact": str,      # LLM-generated
    "estimated_cost_change": float,  # percentage float: -100.0=pause, +20.0=20% increase
    "kpi_context": list[dict],   # kpi_results from AnalyticsSummary
    "status": "pending_approval"
}
```

---

## Recommendation Type Rules

### Underperformers (Red / Amber)

| Score | Worst KPI | Type | Cost Change |
|---|---|---|---|
| < −40% | any | `pause` | −100% of spend |
| −40% to −20% | `spend`, `cpc`, `cpm` | `increase_budget` | +20% |
| −40% to −20% | `ctr`, `conversion_rate` | `swap_creative` | +5% |
| −20% to −10% (amber) | any | `adjust_targeting` | 0% |

### Overperformers (Green, score > +10%)

| Score | Type | Cost Change |
|---|---|---|
| > +30% | `extend_duration` | +15% |
| +10% to +30% | `add_activation` | +25% |

---

## LLM Enrichment

- **Model:** `claude-sonnet-4-20250514`
- **Call pattern:** single `messages.create` with all candidates batched as JSON in the user turn
- **System prompt:** instructs the model to return a JSON array with one object per candidate containing only `activation_id`, `rationale`, `expected_impact`
- **Failure handling:** JSON parse error or API exception → log warning, use fallback strings (`"See KPI context"` / `"Impact not estimated"`), still return all recommendations

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Empty activations list | Return `[]` immediately |
| Fewer than 3 under/over | Return what's available (no padding) |
| LLM call fails / bad JSON | Log warning, apply fallback strings, return recommendations |
| Activation missing `kpi_results` | Skip activation, log warning |
| All activations green (no underperformers) | Return overperformer recommendations only |

---

## Celery Beat Task

**File:** `backend/app/tasks/replanning_tasks.py`

- Task name: `"replanning.run_weekly_replan"`
- Base: `AsyncTask` (same pattern as `analytics_tasks.py`)
- Args: `mandate_id: str`
- Builds `AsyncAnthropic` client from env `ANTHROPIC_API_KEY`
- Calls `AnalyticsAgent.run_daily_analysis()` to get a fresh `AnalyticsSummary`, then passes it to `ReplanningAgent.run_weekly_replan()`
- Schedule: weekly (configured in Celery Beat schedule, outside this scope)

---

## Tests

**File:** `backend/tests/agents/test_replanning_agent.py`

| # | Test | Coverage |
|---|---|---|
| 1 | `test_scorer_ranks_underperformers` | Worst KPI picked, Red/Amber filtered, top 3 limit |
| 2 | `test_scorer_ranks_overperformers` | Green + >+10% filter, top 3 limit |
| 3 | `test_mapper_pause_on_severe_miss` | achievement < −40% → `pause` |
| 4 | `test_mapper_swap_creative_on_ctr_miss` | CTR miss −20% to −40% → `swap_creative` |
| 5 | `test_mapper_extend_duration_on_overperform` | score > +30% → `extend_duration` |
| 6 | `test_enricher_parses_llm_response` | Valid JSON → rationale/impact populated |
| 7 | `test_enricher_fallback_on_bad_json` | Bad LLM response → fallback strings, no exception |
| 8 | `test_agent_full_run` | End-to-end with mocked LLM, 3 under + 3 over returned |
| 9 | `test_agent_empty_summary` | Empty activations → returns `[]` |
| 10 | `test_agent_fewer_than_three` | Only 1 underperformer → returns 1 recommendation |

All tests use `unittest.mock.AsyncMock` for Anthropic client. No DB required.

---

## Constraints

- Output is read-only recommendations — no DB writes, no plan mutations
- `status: "pending_approval"` on every record — AGT-6 approval gate required before any action
- `tenant_id` is propagated from AnalyticsSummary activation entries
- One agent file only: `replanning_agent.py`
