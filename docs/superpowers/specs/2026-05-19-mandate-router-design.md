# Mandate Router Design — 2026-05-19

## Scope

Extend `backend/app/routers/mandate.py` with 5 CRUD + lifecycle endpoints.
Create `mandate_service.py`, `mandate_tasks.py`, and `schemas/mandate.py`.

Existing CI analyze-competitors and job-polling endpoints in `mandate.py` are unchanged.

## New Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/mandates | Create mandate, dispatch AGT-01 |
| GET | /api/v1/mandates/{id} | Fetch mandate (tenant-scoped) |
| PUT | /api/v1/mandates/{id} | Update mandate (draft status only) |
| POST | /api/v1/mandates/{id}/confirm | Confirm summary card, dispatch campaign strategy |
| GET | /api/v1/mandates/{id}/summary-card | Get AGT-01 output from MongoDB |

## Status Machine

```
draft → analyzing → analyzed → confirmed
```

- `draft`: set on creation
- `analyzing`: set by `mandate_tasks.run_mandate_analysis` when AGT-01 starts
- `analyzed`: set by task when AGT-01 completes and stores result to MongoDB
- `confirmed`: set by POST /mandates/{id}/confirm

## Data Storage

- Mandate record: SQLAlchemy / Postgres (`backend/app/models/mandate.py` — existing model)
- AGT-01 summary card output: MongoDB, collection `mandate_analyses`, keyed by `mandate_id` + `tenant_id`

## Files

### `backend/app/schemas/mandate.py` (new)

```python
class CreateMandateRequest(BaseModel):
    name: str
    client_id: str
    objective: str
    region: str
    total_budget: float
    currency: str
    start_date: date
    end_date: date
    description: str | None = None
    countries: list[str] = []
    competitors: list[str] = []

class UpdateMandateRequest(BaseModel):
    name: str | None = None
    objective: str | None = None
    region: str | None = None
    total_budget: float | None = None
    currency: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None
    countries: list[str] | None = None
    competitors: list[str] | None = None

class MandateResponse(BaseModel):
    id: str
    tenant_id: str
    client_id: str
    name: str
    status: str
    objective: str
    region: str
    total_budget: float
    currency: str
    start_date: date
    end_date: date
    description: str | None
    countries: list[str]
    competitors: list[str]
    created_at: datetime
    updated_at: datetime
```

### `backend/app/services/mandate_service.py` (new)

Methods:
- `create(data: CreateMandateRequest, user_id: str, tenant_id: str, db) -> Mandate`
- `get(mandate_id: str, tenant_id: str, db) -> Mandate`  — raises 404 if missing
- `update(mandate_id: str, data: UpdateMandateRequest, tenant_id: str, db) -> Mandate`  — raises 409 if status != draft
- `confirm(mandate_id: str, tenant_id: str, db) -> Mandate`  — raises 400 if status != analyzed
- `get_summary_card(mandate_id: str, tenant_id: str, mongo_db) -> dict`  — raises 404 if not found

### `backend/app/tasks/mandate_tasks.py` (new)

```python
@celery_app.task
def run_mandate_analysis(mandate_id: str, tenant_id: str) -> None:
    # 1. Set mandate.status = "analyzing"
    # 2. Instantiate AGT-01 MandateAnalyst
    # 3. Run analysis
    # 4. Store result to MongoDB mandate_analyses: {mandate_id, tenant_id, ...output}
    # 5. Set mandate.status = "analyzed"
```

### `backend/app/routers/mandate.py` (extend)

Add router prefix `/api/v1/mandates`. Dependencies: `get_db`, `get_mongo_db`, `current_user`, `get_current_tenant`.

```
POST /               → MandateService.create → run_mandate_analysis.delay
GET  /{id}           → MandateService.get
PUT  /{id}           → MandateService.update
POST /{id}/confirm   → MandateService.confirm → run_campaign_strategy.delay
GET  /{id}/summary-card → MandateService.get_summary_card
```

## Error Handling

| Condition | HTTP Code |
|-----------|-----------|
| Mandate not found (wrong id or tenant) | 404 |
| PUT on non-draft mandate | 409 |
| Confirm on non-analyzed mandate | 400 |
| Summary card not yet available | 404 |

## Testing

Extend `backend/tests/routers/test_mandate_router.py` with:
- POST: happy path (201 + Celery dispatched), validation error (422)
- GET: happy path, 404
- PUT: happy path (200), 409 conflict on non-draft
- POST /confirm: happy path (200 + campaign task dispatched), 400 if not analyzed
- GET /summary-card: happy path (200), 404 if missing

Mocking strategy:
- Override `get_db`, `get_mongo_db`, `current_user`, `get_current_tenant`
- Patch `MandateService` class-level (same pattern as `CampaignService`)
- Patch `run_mandate_analysis.delay` and `run_campaign_strategy.delay`

## Remaining Gaps

- AGT-01 full implementation (MandateAnalyst agent) — separate task
- MongoDB integration test for summary card retrieval — deferred to CI
