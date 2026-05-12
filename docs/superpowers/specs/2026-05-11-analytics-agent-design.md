# TASK-020: Analytics Agent (AGT-13) - Design Spec

> **Task**: Build a daily scheduled analytics agent that pulls live activation metrics, computes KPI achievement, flags Red/Amber status, and generates analytics summaries for dashboard.
>
> **Scope**: `backend/app/agents/analytics_agent.py` ONLY (single file, focused agent)

---

## Overview

**AnalyticsAgent** is a Celery Beat scheduled task that runs every 24 hours and:
1. Fetches metrics from platform tools (Google Ads, Meta, LinkedIn) for all live activations
2. Stores metrics in `PerformanceMetric` table (one row = activation + date + metrics)
3. Computes KPI achievement vs targets using flexible, extensible metrics
4. Flags activations as **Red** (>20% below target), **Amber** (10-20% below), or **Green**
5. Generates `AnalyticsSummary` JSON per mandate (for dashboard API)
6. Sends alert notifications when any KPI goes Red

**Output**: Structured `AnalyticsSummary` JSON with per-activation KPI results and alert list.

---

## Architecture

### High-Level Flow

```
Celery Beat (daily) →
  AnalyticsAgent.run() →
    For each Live Activation:
      1. Fetch metrics from platform tool
      2. Store in PerformanceMetric table
      3. Fetch KPIs for this activation
      4. Compute achievement: (actual - target) / target * 100%
      5. Flag status (Red/Amber/Green) per KPI
      6. Build summary entry
    7. Generate AnalyticsSummary JSON
    8. Send alert if any KPI is Red
    → Return AnalyticsSummary for dashboard API
```

### Component Responsibilities

**AnalyticsAgent**:
- Orchestrates daily metrics collection and analysis
- Queries live activations from database
- Calls platform tools via dependency injection
- Computes KPI achievement and status
- Generates AnalyticsSummary JSON
- Triggers alert notifications
- Handles errors gracefully (skip broken activations, continue)

**Platform Tools** (existing):
- `tools.google_ads.get_metrics(activation)` → {impressions, clicks, spend, conversions, ...}
- `tools.meta_ads.get_metrics(activation)` → {...}
- `tools.linkedin_ads.get_metrics(activation)` → {...}

**Services** (new):
- `KPIService`: Fetch KPIs for a campaign/channel/audience
- `PerformanceMetricService`: Store and retrieve daily metrics
- `AnalyticsSummaryService`: Build summary JSON, determine Red/Amber/Green flags

---

## Data Models

### KPI Table (`kpi`)

Stores campaign-level KPI targets, configurable per channel and audience segment.

```
kpi (id, campaign_id, channel_enum, audience_segment)
├── id: UUID (PK)
├── campaign_id: UUID (FK → campaign)
├── channel_enum: String (google_ads, meta_ads, linkedin_ads)
├── audience_segment: String (brand_aware, consideration, etc.)
├── kpi_name: String (conversion_rate, cost_per_click, click_through_rate, roas, cost_per_conversion)
├── target_value: Float (e.g., 3.0 for 3%, 1.50 for $1.50)
├── threshold_unit: String (percent, currency, ratio, count)
├── tenant_id: UUID (multi-tenant isolation)
├── created_at: DateTime
├── updated_at: DateTime
└── Unique constraint: (campaign_id, channel_enum, audience_segment, kpi_name, tenant_id)
```

### PerformanceMetric Table (`performance_metric`)

Stores daily metrics pulled from platform tools. One row per activation per day.

```
performance_metric (id, activation_id, date)
├── id: UUID (PK)
├── activation_id: UUID (FK → activation)
├── date: Date (metrics collection date)
├── metrics_json: JSON (flexible: {impressions, clicks, conversions, spend, ctr, cpc, roas, ...})
├── source: String (google_ads, meta_ads, linkedin_ads)
├── tenant_id: UUID (multi-tenant)
├── created_at: DateTime
└── Indexes: (activation_id, date), (date, tenant_id)
```

**Metrics JSON schema** (flexible, extensible):
```json
{
  "impressions": 5000,
  "clicks": 250,
  "conversions": 7,
  "spend": 500.00,
  "ctr": 0.05,
  "cpc": 2.00,
  "cost_per_conversion": 71.43,
  "roas": 1.2,
  "engagement_rate": 0.08
}
```

### AnalyticsSummary (JSON Response)

Structured summary per mandate, used by dashboard API endpoint.

```json
{
  "mandate_id": "550e8400-e29b-41d4-a716-446655440000",
  "date": "2026-05-11",
  "summary_generated_at": "2026-05-12T08:00:00Z",
  "activations": [
    {
      "activation_id": "uuid",
      "campaign_id": "uuid",
      "channel": "google_ads",
      "sub_channel": "Google Search",
      "status": "red",
      "kpi_results": [
        {
          "kpi_name": "conversion_rate",
          "target": 3.0,
          "actual": 2.1,
          "achievement_percent": -30.0,
          "threshold_unit": "percent",
          "status": "red"
        },
        {
          "kpi_name": "cost_per_click",
          "target": 1.50,
          "actual": 1.45,
          "achievement_percent": 3.33,
          "threshold_unit": "currency",
          "status": "green"
        }
      ],
      "metrics": {
        "impressions": 5000,
        "clicks": 250,
        "conversions": 7,
        "spend": 500.00
      }
    },
    {
      "activation_id": "uuid",
      "channel": "meta_ads",
      "status": "amber",
      "kpi_results": [
        {
          "kpi_name": "roas",
          "target": 3.0,
          "actual": 2.7,
          "achievement_percent": -10.0,
          "status": "amber"
        }
      ]
    }
  ],
  "red_alerts": [
    {
      "activation_id": "uuid",
      "channel": "google_ads",
      "failed_kpi": "conversion_rate",
      "severity": "red"
    }
  ],
  "summary_by_channel": {
    "google_ads": {"total": 5, "red": 1, "amber": 1, "green": 3},
    "meta_ads": {"total": 4, "red": 0, "amber": 2, "green": 2},
    "linkedin_ads": {"total": 2, "red": 0, "amber": 0, "green": 2}
  }
}
```

---

## Achievement Calculation & Flagging

### Formula

For each KPI:
```
achievement_percent = ((actual - target) / target) * 100
```

**Examples**:
- Target: 3.0% CTR, Actual: 2.4% → achievement = ((2.4 - 3.0) / 3.0) * 100 = -20.0%
- Target: $1.50 CPC, Actual: $1.55 → achievement = ((1.55 - 1.50) / 1.50) * 100 = +3.33%

### Status Mapping

```
status = {
  "red"    if achievement_percent < -20
  "amber"  if -20 ≤ achievement_percent < -10
  "green"  if achievement_percent ≥ -10
}
```

### Activation-Level Status

- **Red**: If ANY KPI is Red
- **Amber**: If ANY KPI is Amber (and none are Red)
- **Green**: If ALL KPIs are Green

---

## Agent Implementation

### Class: AnalyticsAgent

```python
class AnalyticsAgent:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.platform_tools = {...}  # google_ads, meta_ads, linkedin_ads
        self.kpi_service = KPIService(db_session)
        self.metric_service = PerformanceMetricService(db_session)
        self.summary_service = AnalyticsSummaryService(db_session)
        self.notification_service = NotificationService()
    
    async def run_daily_analysis(self) -> AnalyticsSummary:
        """Main Celery Beat task entry point."""
        # 1. Fetch all live activations
        # 2. Group by mandate for summary generation
        # 3. For each activation: fetch metrics, store, compute KPIs
        # 4. Build AnalyticsSummary
        # 5. Send alerts for Red KPIs
        # 6. Return summary
    
    async def analyze_activation(activation: Activation) -> ActivationAnalysis:
        """Analyze single activation."""
        # 1. Fetch metrics from platform tool
        # 2. Store in PerformanceMetric
        # 3. Fetch KPIs for this activation
        # 4. Compute achievement for each KPI
        # 5. Return analysis result
```

### Method: fetch_metrics(activation)

Calls appropriate platform tool based on `activation.channel_enum`.

Returns: Metrics dict (flexible JSON schema)

Error handling: Log warning, return None (skip this activation)

### Method: compute_kpi_achievement(kpi, actual_metrics)

Extracts metric from `actual_metrics` dict (flexible key matching: "conversion_rate" → "conversions" / "clicks").

Computes: `(actual - target) / target * 100`

Returns: Achievement %, Status (Red/Amber/Green)

### Method: send_red_alerts(summary)

If `summary.red_alerts` is non-empty:
- Fetch campaign manager contact from Campaign record
- Build alert message: "KPI Alert: [Activation] [Channel] [KPI Name] is RED (30% below target)"
- Send email + WhatsApp notification

---

## Error Handling

| Error | Handling |
|-------|----------|
| Platform API unavailable | Log warning, skip activation, continue with others |
| No KPIs defined for activation | Log info, include in summary with `status: "no_kpis"` |
| Metrics JSON malformed | Log error, skip activation |
| Database insert fails | Retry 3x, then fail task and alert ops |
| Missing campaign manager contact | Log warning, skip notification for that activation |

---

## Testing Strategy

**Unit Tests**:
- KPI achievement calculation (edge cases: division by zero, negative targets)
- Status flagging logic (Red/Amber/Green boundaries)
- AnalyticsSummary JSON structure validation
- Metrics extraction from flexible JSON

**Integration Tests**:
- Mock platform tools, verify metrics storage in DB
- Fetch KPIs, compute achievements, verify summary output
- Test error scenarios (missing KPIs, API failures)
- Verify alert notification triggering for Red KPIs

**End-to-End Tests**:
- Celery Beat scheduling verification
- Full daily analysis workflow
- Summary JSON returned and accessible via dashboard API

---

## Constraints & Assumptions

- **24-hour schedule**: Metrics collected once per day (typically overnight)
- **Flexible metrics**: Platform tools return different metric sets; agent must handle gracefully
- **KPI query**: Most activations will have 2-5 KPIs; no hard limit
- **Single mandate per run**: Agent processes one mandate at a time (Celery Beat manages scheduling)
- **No real-time updates**: This is daily batch analysis, not real-time monitoring

---

## Future Extensibility

- Add more platform tools (TikTok, Pinterest, etc.) without changing agent
- Add custom metric derivation (e.g., "efficiency_score" = ROAS / CPC)
- Support for weekly/monthly analysis (not just daily)
- Threshold customization per mandate/campaign
- Historical trend analysis (Red streak detection, anomaly flags)

---

## Success Criteria

✅ Agent runs daily via Celery Beat  
✅ All live activations analyzed and metrics stored  
✅ KPI achievement computed correctly for each activation  
✅ Red/Amber/Green flags accurate per spec  
✅ AnalyticsSummary JSON generated with all required fields  
✅ Alert notifications sent for Red KPIs  
✅ Dashboard API can fetch and display summary  
✅ Graceful error handling (no task failure on single activation error)  
✅ 80%+ test coverage  
