# TASK-012 Campaign Router — Design Spec

**Date:** 2026-05-11  
**Task:** TASK-012  
**Module scope:** `backend/app/routers/campaign.py` + `backend/app/services/campaign_service.py`

---

## 1. Purpose

Expose 7 REST endpoints for the campaign lifecycle: create (triggers AGT-03), read, update, confirm concept, get/trigger activation plan (AGT-04), propose budget (AGT-05), and confirm budget. All routes are JWT-protected and `tenant_id`-scoped.

---

## 2. Architecture

**Two files:**
- `backend/app/routers/campaign.py` — HTTP only: auth deps, request parsing, response serialisation, delegate to service
- `backend/app/services/campaign_service.py` — all business logic, MongoDB queries, agent calls

**MongoDB collection:** `campaigns`  
Every query includes `tenant_id` filter — mandatory.

### Endpoint table

| Method | Path | Service method | Status transition |
|---|---|---|---|
| POST | `/api/v1/campaigns` | `create()` | → `concepts_ready` |
| GET | `/api/v1/campaigns/{id}` | `get()` | — |
| PUT | `/api/v1/campaigns/{id}` | `update()` | — |
| POST | `/api/v1/campaigns/{id}/confirm` | `confirm()` | `concepts_ready` → `confirmed` |
| GET | `/api/v1/campaigns/{id}/activation-plan` | `get_activation_plan()` | `confirmed` → `planned` |
| POST | `/api/v1/campaigns/{id}/approve-budget` | `propose_budget()` | `planned` → `budget_proposed` |
| POST | `/api/v1/campaigns/{id}/confirm-budget` | `confirm_budget()` | `budget_proposed` → `approved` |

---

## 3. Data Models

### 3.1 MongoDB document (`campaigns` collection)

```json
{
  "_id": "<uuid4>",
  "tenant_id": "<str>",
  "mandate_id": "<str>",
  "status": "pending|concepts_ready|confirmed|planned|budget_proposed|approved",
  "concepts": [<CampaignConcept>, ...],
  "selected_concept_id": "<uuid4> | null",
  "activation_plan": [<Activation>, ...] | null,
  "budget_proposal": {<BudgetBreakdown>} | null,
  "created_at": "<ISO datetime>",
  "updated_at": "<ISO datetime>"
}
```

`concepts` holds 3 `CampaignConcept` objects (AGT-03 output). `activation_plan` is AGT-04 output. `budget_proposal` is AGT-05 output.

### 3.2 Pydantic request/response schemas (defined in `routers/campaign.py`)

| Schema | Fields |
|---|---|
| `CampaignCreateRequest` | `mandate_id: str` |
| `CampaignUpdateRequest` | `mandate_id: str \| None`, `selected_concept_id: str \| None` |
| `CampaignConfirmRequest` | `selected_concept_id: str` |
| `CampaignResponse` | all document fields |
| `ActivationPlanResponse` | `campaign_id`, `activation_plan`, `status` |
| `BudgetProposalResponse` | `campaign_id`, `budget_proposal`, `status` |

### 3.3 Status machine

```
pending → concepts_ready → confirmed → planned → budget_proposed → approved
```

Note: `pending` is a transient state during the AGT-03 call; the document is inserted as `concepts_ready` once the agent returns. No document is persisted in `pending` state.

---

## 4. Service Layer Logic

### `CampaignService(db: AsyncIOMotorDatabase)`

**`create(mandate_id, tenant_id)`**
1. `mandates.find_one({_id: mandate_id, tenant_id})` → 404 if missing
2. `ci_reports.find_one({mandate_id, tenant_id}, sort=-created_at)` → 404 if none
3. `await campaign_strategist_agent(mandate, ci_report)` → 3 `CampaignConcept` objects
4. Insert `campaigns` doc: status=`concepts_ready`, concepts=3 items
5. Return doc

**`get(campaign_id, tenant_id)`**
- `campaigns.find_one({_id, tenant_id})` → 404 if missing

**`update(campaign_id, tenant_id, payload)`**
- Find → 404; patch provided fields + `updated_at`; return updated doc

**`confirm(campaign_id, selected_concept_id, tenant_id)`**
- Find → 404; status ≠ `concepts_ready` → 409
- `selected_concept_id` not in concepts array → 422
- Set `selected_concept_id`, status=`confirmed`, `updated_at`

**`get_activation_plan(campaign_id, tenant_id)`**
- Find → 404; status not in {`confirmed`, `planned`, `budget_proposed`, `approved`} → 409
- `activation_plan` already set → return cached (no agent call)
- Else: call `media_planner_agent(selected_concept, budget_envelope)`; persist; status=`planned`

**`propose_budget(campaign_id, tenant_id)`**
- Find → 404; status ≠ `planned` → 409
- Call `budget_optimizer_agent(activation_plan)`; persist proposal; status=`budget_proposed`

**`confirm_budget(campaign_id, tenant_id)`**
- Find → 404; status ≠ `budget_proposed` → 409
- Set status=`approved`, `updated_at`; return doc

---

## 5. Error Handling

| Condition | HTTP status |
|---|---|
| Campaign / mandate / CI report not found | 404 |
| State machine guard violated | 409 |
| `selected_concept_id` not in concepts array | 422 |
| Agent raises `ValueError` (input validation) | 400 |
| Agent raises any other exception | 500 |
| Missing / mismatched `X-Tenant-ID` | 401/403 (middleware) |

All errors raised as `HTTPException(status_code=..., detail="<human-readable>")`.

---

## 6. Auth Pattern

Matches existing mandate router:

```python
from backend.app.core.auth import current_user
from backend.app.core.dependencies import get_current_tenant
from backend.app.core.models import User

@router.post("/campaigns")
async def create_campaign(
    body: CampaignCreateRequest,
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncIOMotorDatabase = Depends(get_db),
): ...
```

---

## 7. Testing

**File:** `backend/tests/agents/test_campaign_service.py`  
**Target coverage:** ≥90%  
All tests mock MongoDB (`AsyncMock`) and agent functions (`AsyncMock`).

| Test | Verifies |
|---|---|
| `test_create_returns_concepts_ready` | Happy path: 3 concepts, status=`concepts_ready` |
| `test_create_404_missing_mandate` | 404 when mandate not in Mongo |
| `test_create_404_missing_ci_report` | 404 when CI report absent |
| `test_get_returns_campaign` | Returns doc with correct `tenant_id` |
| `test_get_404_wrong_tenant` | 404 when tenant_id mismatch |
| `test_confirm_sets_selected_concept` | Status → `confirmed`, concept_id stored |
| `test_confirm_409_wrong_status` | 409 when status ≠ `concepts_ready` |
| `test_confirm_422_invalid_concept_id` | 422 when concept_id not in array |
| `test_get_activation_plan_triggers_agt04` | AGT-04 called; status → `planned` |
| `test_get_activation_plan_cached` | AGT-04 not called if plan already stored |
| `test_get_activation_plan_409_not_confirmed` | 409 when status < `confirmed` |
| `test_propose_budget_triggers_agt05` | AGT-05 called; status → `budget_proposed` |
| `test_propose_budget_409_wrong_status` | 409 when status ≠ `planned` |
| `test_confirm_budget_sets_approved` | Status → `approved` |
| `test_confirm_budget_409_wrong_status` | 409 when status ≠ `budget_proposed` |

---

## 8. Integration Points

| Upstream | What is consumed |
|---|---|
| AGT-03 `campaign_strategist_agent()` | `(mandate_dict, ci_report_dict)` → `List[CampaignConcept]` |
| AGT-04 `media_planner_agent()` | `(selected_concept, budget_envelope)` → activation plan list |
| AGT-05 `budget_optimizer_agent()` | `(activation_plan)` → budget breakdown dict |
| MongoDB `mandates` collection | fetch by `{_id: mandate_id, tenant_id}` |
| MongoDB `ci_reports` collection | fetch latest by `{mandate_id, tenant_id}` |

AGT-06, AGT-07 are not called by this router.

---

## 9. Out of Scope

- Celery background tasks (all agent calls are synchronous)
- Pagination on GET /campaigns list (single-doc GET only)
- Campaign deletion
- WebSocket / streaming responses
- AGT-06 / AGT-07 integration (separate tasks)
