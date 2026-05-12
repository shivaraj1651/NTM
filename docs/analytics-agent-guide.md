# Analytics Agent (AGT-13) Implementation Guide

## Overview
The Analytics Agent is a Celery Beat scheduled task that runs every 24 hours to analyze activation performance against KPI targets.

## Architecture

### Data Flow
1. **Fetch Activations** → Query live activations for mandate
2. **Fetch Metrics** → Call platform tools (Google Ads, Meta, LinkedIn)
3. **Store Metrics** → Insert into PerformanceMetric table
4. **Compute KPIs** → Compare actual vs target, calculate achievement %
5. **Flag Status** → Red (<-20%), Amber (-20% to -10%), Green (≥-10%)
6. **Generate Summary** → Build AnalyticsSummary JSON per mandate
7. **Send Alerts** → Email + WhatsApp for Red KPIs

### File Structure
```
backend/app/
├── agents/
│   └── analytics_agent.py          # Main agent orchestrator
├── models/
│   ├── kpi.py                      # KPI target definition
│   └── performance_metric.py        # Daily metrics storage
├── services/
│   ├── kpi_service.py              # Fetch KPIs
│   ├── performance_metric_service.py # Store/retrieve metrics
│   └── analytics_summary_service.py  # Compute KPI achievement & status
└── tasks/
    └── analytics_tasks.py           # Celery Beat task registration
```

## KPI Achievement Formula

```
achievement_percent = ((actual - target) / target) * 100
```

**Examples:**
- Target: 3.0% CTR, Actual: 2.4% → achievement = ((2.4 - 3.0) / 3.0) * 100 = -20.0%
- Target: $1.50 CPC, Actual: $1.55 → achievement = ((1.55 - 1.50) / 1.50) * 100 = +3.33%

## Status Mapping

| Achievement % | Status | Severity |
|---|---|---|
| < -20% | Red | Critical - KPI far below target |
| -20% to -10% | Amber | Warning - KPI below target |
| ≥ -10% | Green | On track - meeting or exceeding target |

## Usage

### Manual Execution
```python
from backend.app.db import SessionLocal
from backend.app.agents.analytics_agent import AnalyticsAgent
from backend.app.tools.google_ads import GoogleAdsTool
from backend.app.tools.meta_ads import MetaAdsTool
from backend.app.tools.linkedin_ads import LinkedInAdsTool
import asyncio

async def run_analysis():
    async with SessionLocal() as db_session:
        platform_tools = {
            "google_ads": GoogleAdsTool(db_session),
            "meta_ads": MetaAdsTool(db_session),
            "linkedin_ads": LinkedInAdsTool(db_session)
        }
        agent = AnalyticsAgent(db_session, platform_tools)
        summary = await agent.run_daily_analysis(mandate_id=mandate_uuid)
        return summary

result = asyncio.run(run_analysis())
```

### Celery Beat Schedule
Task registered in `backend/app/celery_app.py`:
```python
'analytics-daily-analysis': {
    'task': 'analytics.run_daily_analysis',
    'schedule': crontab(hour=0, minute=0),  # Runs daily at midnight UTC
}
```

## Dashboard API Integration

The AnalyticsSummary JSON is used by the dashboard API endpoint to display:
- Per-activation KPI results with achievement %
- Red/Amber/Green status indicators
- Channel-level summary counts
- Red alert list for quick action

## Error Handling

| Error | Handling |
|---|---|
| Platform API unavailable | Log warning, skip activation, continue with others |
| No KPIs defined | Log info, skip activation |
| Metrics JSON malformed | Log error, skip activation |
| Missing campaign contact | Log warning, skip notification |

## Testing

Run all tests:
```bash
pytest tests/unit/agents/test_analytics_agent.py -v
pytest tests/unit/services/test_analytics_summary_service.py -v
pytest tests/integration/test_analytics_end_to_end.py -v
```

Coverage target: 80%+

## Success Criteria

✅ Agent runs daily via Celery Beat  
✅ All live activations analyzed  
✅ Metrics stored correctly  
✅ KPI achievement computed accurately  
✅ Red/Amber/Green flags correct  
✅ AnalyticsSummary JSON complete  
✅ Alert notifications sent for Red KPIs  
✅ Graceful error handling (no crash on single activation error)  
✅ 80%+ test coverage
