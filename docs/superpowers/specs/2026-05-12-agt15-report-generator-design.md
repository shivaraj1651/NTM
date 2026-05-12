# AGT-15 Report Generator — Design Spec

## Overview

AGT-15 is a report generation agent that consumes outputs from AGT-13 (AnalyticsAgent) and AGT-14 (ReplanningAgent) to produce structured campaign performance reports for two audiences:

- **Internal** (campaign managers): operational detail — activation status, KPI breakdown, replanning recommendations
- **External** (clients): executive narrative — spend vs. results, trends, key insights

Two report modes:
- **Daily digest**: data-only, triggered after AGT-13, internal audience
- **Weekly full report**: data + 7-day trends + LLM narrative, triggered after AGT-14, both audiences

Reports are persisted to DB via a new `Report` model and returned as structured dicts.

---

## Architecture

### File

`backend/app/agents/report_generator.py`

### Classes

```
ReportAgent                     # orchestrator — public interface
├── DailyDigestBuilder          # computes daily data-only digest from AnalyticsSummary
├── TrendAnalyzer               # queries PerformanceMetric for 7-day window, computes trends
├── WeeklyReportBuilder         # assembles weekly report dict from summary + trends + replan recs
└── LLMNarrator                 # fires one Anthropic call → executive_summary + key_insights
```

### Constructor

```python
ReportAgent(db_session: AsyncSession, anthropic_client: Any)
```

- `db_session` — for Report persistence (via `ReportService`) and TrendAnalyzer queries
- `anthropic_client` — passed to `LLMNarrator` (weekly only)

### Public Methods

```python
async run_daily(mandate_id: str, tenant_id: str, analytics_summary: dict) -> dict
async run_weekly(mandate_id: str, tenant_id: str, analytics_summary: dict, replan_recommendations: list[dict]) -> dict
```

---

## Component Responsibilities

### DailyDigestBuilder

Transforms an `AnalyticsSummary` dict (from AGT-13) into a daily report dict.
Pure computation — no I/O.

```python
def build(mandate_id: str, analytics_summary: dict) -> dict
```

### TrendAnalyzer

Queries `PerformanceMetric` table for the past 7 days per activation, aggregates:
- Total impressions, clicks, spend, conversions over the window
- Per-channel rollup
- Simple trend label: `"improving"` | `"stable"` | `"declining"` based on day-over-day spend delta

```python
async def analyze(activation_ids: list[str], tenant_id: str, week_end: date) -> dict[str, dict]
```

`activation_ids` is extracted from `analytics_summary["activations"]` by the orchestrator before calling.

Returns: `{ channel: { impressions_7d, clicks_7d, spend_7d, conversions_7d, trend } }`

### WeeklyReportBuilder

Assembles the full weekly report dict from:
- `analytics_summary` (AGT-13 output)
- `trends` (TrendAnalyzer output)
- `replan_recommendations` (AGT-14 output)

Pure computation — no I/O.

```python
def build(mandate_id: str, analytics_summary: dict, trends: dict, replan_recommendations: list[dict]) -> dict
```

### LLMNarrator

Fires one Anthropic call with a structured prompt containing the weekly report dict. Extracts:
- `executive_summary`: 2–3 sentence client-facing narrative
- `key_insights`: list of 3 bullet-point strings

Falls back to `"Summary unavailable"` / `[]` on any LLM failure.

```python
async def narrate(weekly_report: dict) -> dict[str, Any]
# Returns: { "executive_summary": str, "key_insights": list[str] }
```

---

## Data Contracts

### Input: `AnalyticsSummary` (dict from AGT-13)

```json
{
  "mandate_id": "uuid",
  "date": "2026-05-12",
  "summary_generated_at": "2026-05-12T08:00:00Z",
  "activations": [
    {
      "activation_id": "uuid",
      "campaign_id": "uuid",
      "channel": "google_ads",
      "status": "red",
      "kpi_results": [
        { "kpi_name": "conversion_rate", "target": 3.0, "actual": 2.1,
          "achievement_percent": -30.0, "status": "red" }
      ],
      "metrics": { "impressions": 5000, "clicks": 250, "spend": 500.0 }
    }
  ],
  "red_alerts": [ { "activation_id": "uuid", "channel": "google_ads", "failed_kpi": "conversion_rate", "severity": "red" } ],
  "summary_by_channel": { "google_ads": { "total": 5, "red": 1, "amber": 2, "green": 2 } }
}
```

### Input: `ReplanRecommendation` list (from AGT-14, weekly only)

```json
[
  {
    "mandate_id": "uuid",
    "activation_id": "uuid",
    "channel": "google_ads",
    "direction": "underperforming",
    "recommendation_type": "swap_creative",
    "rationale": "...",
    "expected_impact": "...",
    "estimated_cost_change": 5.0,
    "status": "pending_approval"
  }
]
```

### Output: Daily Digest

```json
{
  "report_type": "daily",
  "mandate_id": "uuid",
  "date": "2026-05-12",
  "generated_at": "2026-05-12T08:05:00Z",
  "summary_by_channel": { "google_ads": { "total": 5, "red": 1, "amber": 2, "green": 2 } },
  "activations": [ { "activation_id": "uuid", "channel": "google_ads", "status": "red", "kpi_results": [...] } ],
  "red_alert_count": 1
}
```

### Output: Weekly Full Report

```json
{
  "report_type": "weekly",
  "mandate_id": "uuid",
  "week_start": "2026-05-06",
  "week_end": "2026-05-12",
  "generated_at": "2026-05-12T10:00:00Z",
  "summary_by_channel": { "google_ads": { "total": 5, "red": 1, "amber": 2, "green": 2 } },
  "activations": [ { "activation_id": "uuid", "channel": "google_ads", "status": "red", "kpi_results": [...] } ],
  "trends": {
    "google_ads": { "impressions_7d": 35000, "clicks_7d": 1750, "spend_7d": 3500.0, "conversions_7d": 49, "trend": "stable" }
  },
  "replan_recommendations": [ { "activation_id": "uuid", "recommendation_type": "swap_creative", "rationale": "..." } ],
  "executive_summary": "LLM-generated 2-3 sentence client narrative...",
  "key_insights": ["Insight 1", "Insight 2", "Insight 3"],
  "red_alert_count": 1
}
```

---

## DB Model — `Report`

**File:** `backend/app/models/report.py`

```
report
├── id: UUID (PK)
├── mandate_id: String (FK reference, indexed)
├── tenant_id: String (multi-tenant isolation, indexed)
├── report_type: String ("daily" | "weekly")
├── period_start: Date
├── period_end: Date
├── report_json: JSON (full output dict)
└── created_at: DateTime
```

**Indexes:**
- `(mandate_id, report_type, period_start)` — for fetching latest report per type
- `(tenant_id, report_type)` — for tenant-scoped listing

**Migration:** Alembic migration for the `report` table.

---

## Service — `ReportService`

**File:** `backend/app/services/report_service.py`

```python
class ReportService:
    async def save(self, report_dict: dict, tenant_id: str) -> Report
    async def get_latest(self, mandate_id: str, report_type: str, tenant_id: str) -> Report | None
```

---

## Celery Beat Tasks

**File:** `backend/app/tasks/report_tasks.py`

| Task | Schedule | After |
|---|---|---|
| `generate_daily_report_task` | Daily 09:00 UTC | AGT-13 at 08:00 UTC |
| `generate_weekly_report_task` | Monday 10:00 UTC | AGT-14 at 09:00 UTC |

Both tasks iterate over all active mandates (per-tenant), calling the appropriate `ReportAgent` method.

---

## Trend Calculation

For the 7-day trend label, `TrendAnalyzer` compares spend of the last 2 days vs. previous 5 days:
- `improving` — last-2-day avg spend > prev-5-day avg spend by > 10%
- `declining` — last-2-day avg spend < prev-5-day avg spend by > 10%
- `stable` — within ±10%

If fewer than 2 days of data exist, `trend = "insufficient_data"`.

---

## LLM Prompt Structure (Weekly Narrator)

Single Anthropic call with `claude-haiku-4-5` (report summary is boilerplate — appropriate for Haiku):

```
System: You are a marketing performance analyst. Write concise, client-appropriate summaries.

User: Summarize the following weekly campaign performance report in 2-3 sentences 
(executive_summary) and provide exactly 3 key insights as a JSON list (key_insights).
Return JSON only: {"executive_summary": "...", "key_insights": ["...", "...", "..."]}

[report dict as JSON]
```

Fallback on parse error: `{"executive_summary": "Summary unavailable", "key_insights": []}`.

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Empty activations list | Return minimal report dict, persist, log warning |
| TrendAnalyzer DB error | Weekly proceeds with `trends: {}`, log warning |
| LLM call fails / bad JSON | Fallback strings applied, report still returned |
| No replan recommendations | Weekly proceeds with `replan_recommendations: []` |
| DB persistence fails | Log error, still return in-memory report dict to caller |

---

## Tests

**File:** `backend/tests/agents/test_report_generator.py`

| Test | Focus |
|---|---|
| `test_daily_digest_builder_structure` | Correct keys, red_alert_count |
| `test_daily_digest_builder_empty_activations` | Returns minimal dict |
| `test_trend_analyzer_7day_aggregation` | Correct channel rollup |
| `test_trend_analyzer_empty_metrics` | Returns empty dict gracefully |
| `test_trend_analyzer_improving_label` | Trend label logic |
| `test_trend_analyzer_declining_label` | Trend label logic |
| `test_weekly_report_builder_assembles_all_sections` | Full dict with all keys |
| `test_weekly_report_builder_no_recommendations` | `replan_recommendations: []` |
| `test_llm_narrator_happy_path` | Extracts summary + insights |
| `test_llm_narrator_fallback_on_bad_json` | Fallback strings applied |
| `test_report_agent_run_daily_end_to_end` | Mocked DB, correct output |
| `test_report_agent_run_weekly_end_to_end` | Mocked DB + LLM, full report |
| `test_report_agent_run_weekly_persists_to_db` | ReportService.save called |
| `test_report_service_save_and_fetch` | DB round-trip |
| `test_report_service_get_latest_returns_none` | No report found |

---

## Constraints

- One agent file only: `report_generator.py`
- All DB queries include `tenant_id`
- LLM calls only in `LLMNarrator`, only for weekly reports
- `run_daily()` and `run_weekly()` are the only public methods on `ReportAgent`
- Haiku model for LLM narration (boilerplate summary generation)
- Output is returned AND persisted — caller does not need to persist separately
