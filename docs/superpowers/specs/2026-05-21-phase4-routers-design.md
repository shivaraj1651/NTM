# Phase 4 Routers Design

**Date:** 2026-05-21
**Scope:** Four async HTTP routers for Phase 4 agents — Digital Activator, Analytics, Replanning, Report Generator.

---

## Context

AGT-12 through AGT-15 are fully implemented agents with Celery task files, services, and models.
They have no HTTP surface. This spec adds one router per agent following the existing `mandate.py` and `campaign.py` patterns.

---

## Architecture

**Module rule:** One router file per agent (`One agent per file` from CLAUDE.md).

**Files created:**
- `backend/app/routers/digital_activator.py`
- `backend/app/routers/analytics.py`
- `backend/app/routers/replanning.py`
- `backend/app/routers/report.py`
- Updated: `backend/app/routers/__init__.py`

**Shared schema (new):**
```python
# backend/app/schemas/jobs.py
class JobQueuedResponse(BaseModel):
    job_id: str
    status: Literal["queued"]
    campaign_id: str
```

---

## Endpoints

### Digital Activator (`/api/v1/campaigns/{campaign_id}/activate`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/campaigns/{campaign_id}/activate` | Trigger activation via Celery → `activation_tasks.activate_campaign.delay(campaign_id, tenant_id)` |

Response: `JobQueuedResponse`

No GET — activation status tracked via existing `GET /api/v1/jobs/{job_id}`.

---

### Analytics (`/api/v1/campaigns/{campaign_id}/analytics`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/campaigns/{campaign_id}/analytics/run` | Trigger analytics ingestion → `analytics_tasks.run_analytics.delay(campaign_id, tenant_id)` |
| GET | `/api/v1/campaigns/{campaign_id}/analytics` | Fetch latest `AnalyticsSummary` from MongoDB. Returns 404 if not yet generated. |

POST response: `JobQueuedResponse`
GET response: `AnalyticsSummaryResponse` (typed from `analytics_summary_service.get_latest`)

---

### Replanning (`/api/v1/campaigns/{campaign_id}/replan`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/campaigns/{campaign_id}/replan` | Trigger replanning → `replanning_tasks.run_replanning.delay(campaign_id, tenant_id)` |

Response: `JobQueuedResponse`

No GET — replan updates campaign document in-place; poll campaign via `GET /api/v1/campaigns/{id}`.

---

### Report (`/api/v1/campaigns/{campaign_id}/report`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/campaigns/{campaign_id}/report/generate` | Trigger weekly report build → `report_tasks.generate_report.delay(campaign_id, tenant_id)` |
| GET | `/api/v1/campaigns/{campaign_id}/report` | Fetch latest report from `report_service.get_latest(campaign_id, tenant_id)`. Returns 404 if not generated. |

POST response: `JobQueuedResponse`
GET response: `ReportResponse` (typed from `report_service` output shape)

---

## Auth Pattern

All endpoints: `Depends(current_user)` + `Depends(get_current_tenant)` + `Depends(get_db)` — identical to `campaign.py`.

---

## Registration

```python
# backend/app/routers/__init__.py
from backend.app.routers.digital_activator import router as digital_activator_router
from backend.app.routers.analytics import router as analytics_router
from backend.app.routers.replanning import router as replanning_router
from backend.app.routers.report import router as report_router

def register_routers(app):
    app.include_router(mandate_router)
    app.include_router(campaign_router)
    app.include_router(creative_director_router)
    app.include_router(digital_activator_router)
    app.include_router(analytics_router)
    app.include_router(replanning_router)
    app.include_router(report_router)
```

---

## Testing

- `backend/tests/routers/test_digital_activator_router.py`
- `backend/tests/routers/test_analytics_router.py`
- `backend/tests/routers/test_replanning_router.py`
- `backend/tests/routers/test_report_router.py`

Each test file: mock the Celery `.delay()` call, assert 201 + job_id returned. GET tests: mock service, assert typed response or 404.

---

## Error Handling

- Campaign not found → 404 (service raises, router catches)
- Tenant mismatch → 403
- Task queue unavailable → 503 (Celery connection error, caught in router, returns `{"detail": "Task queue unavailable"}`)
