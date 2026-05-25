# Audit Trail System — Design Spec
**Date:** 2026-05-25  
**Session:** audit  
**Stack:** Python 3.12, FastAPI, SQLAlchemy async, PostgreSQL 16, React 18, TypeScript, shadcn/ui

---

## 1. Goal

Replace the narrow `ApprovalLog` (approval state transitions only) with a general-purpose `audit_trail` table that captures all CRUD operations and agent/tool events across every entity in the NTM platform. Wire the existing `AuditLogPage.tsx` frontend to the real API.

`ApprovalLog` is **not removed** — it remains for approval-specific workflows.

---

## 2. Data Model

### Table: `audit_trail` (insert-only)

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | String (UUID) | No | PK, auto-generated |
| `tenant_id` | String | No | Required — NTM multi-tenant rule |
| `entity_type` | String | No | `mandate`, `campaign`, `creative`, `budget`, `kpi`, `user`, `tenant`, `agent_run`, `tool_call` |
| `entity_id` | String | No | Reference ID; no FK constraint |
| `action` | String | No | `create`, `read`, `update`, `delete`, `agent_run`, `tool_call` |
| `actor_id` | String | No | User ID from JWT; `"anonymous"` if unauthenticated |
| `actor_role` | String | Yes | Role from JWT claims |
| `ip_address` | String | Yes | From `X-Forwarded-For` or `request.client.host` |
| `user_agent` | String | Yes | From `User-Agent` header |
| `request_path` | String | Yes | e.g. `/api/v1/campaign/123` |
| `payload_before` | JSON | Yes | Snapshot before update/delete |
| `payload_after` | JSON | Yes | Snapshot after create/update |
| `status` | String | No | `success` \| `error` |
| `error_message` | Text | Yes | Populated when `status = "error"` |
| `created_at` | DateTime(tz) | No | UTC, immutable |

### Indexes

```sql
ix_audit_trail_tenant              (tenant_id)
ix_audit_trail_entity_type         (entity_type)
ix_audit_trail_actor               (actor_id)
ix_audit_trail_tenant_entity_type  (tenant_id, entity_type)
ix_audit_trail_tenant_created      (tenant_id, created_at DESC)
```

---

## 3. Context Propagation

### `backend/app/core/audit_context.py`

Single `ContextVar` holding per-request actor metadata:

```python
from contextvars import ContextVar

_audit_ctx: ContextVar[dict] = ContextVar("audit_ctx", default={})

def set_audit_context(data: dict) -> Token: ...
def get_audit_context() -> dict: ...
def reset_audit_context(token: Token) -> None: ...
```

Fields: `actor_id`, `actor_role`, `tenant_id`, `ip_address`, `user_agent`, `request_path`.

### `backend/app/core/audit_middleware.py`

`BaseHTTPMiddleware` subclass:

- Runs before every request
- Extracts JWT claims via existing `core.auth` helpers
- Sets `_audit_ctx` token; resets via `token` after response (async-safe)
- If JWT missing or invalid → sets `actor_id = "anonymous"`, never blocks the request
- Registered in `main.py` after auth middleware

---

## 4. AuditService

### `backend/app/services/audit_service.py`

```python
class AuditService:
    def __init__(self, db: AsyncSession) -> None: ...

    async def emit(
        self,
        entity_type: str,
        entity_id: str,
        action: str,
        payload_before: dict | None = None,
        payload_after: dict | None = None,
        status: str = "success",
        error_message: str | None = None,
    ) -> None:
        """Insert one AuditTrail row. Never raises — logs errors internally."""
```

- Reads actor context from `_audit_ctx` ContextVar
- **Happy path** (`status="success"`): inserts `AuditTrail` row in the caller's transaction via `db.add` + `await db.flush()`
- **Error path** (`status="error"`): uses a **separate** `AsyncSession` (obtained from `async_sessionmaker` directly) so the audit row commits even if the caller's transaction rolled back
- On any exception inside `emit()`: logs at WARNING level, does not propagate

### Dependency

```python
async def get_audit_service(db: AsyncSession = Depends(get_db)) -> AuditService:
    return AuditService(db)
```

Injected as `audit: AuditService = Depends(get_audit_service)`.

---

## 5. Router Instrumentation

Routers call `await audit.emit(...)` **after** the main operation succeeds.

| Router | Endpoints instrumented | Actions |
|---|---|---|
| `mandate.py` | create, update, delete | `create`, `update`, `delete` |
| `campaign.py` | create, update, delete | `create`, `update`, `delete` |
| `creatives.py` | create, update, delete | `create`, `update`, `delete` |
| `admin.py` | tenant create, user create, role assign | `create`, `update` |
| `analytics.py` | run analytics | `agent_run` |
| `replanning.py` | trigger replan | `agent_run` |
| `report.py` | generate report | `agent_run` |

`payload_before` populated for `update` and `delete` (snapshot fetched before mutation).  
`payload_after` populated for `create` and `update`.

---

## 6. Audit Router

### `backend/app/routers/audit.py`

**Prefix:** `/api/v1/admin/audit-trail`  
**Auth:** `platform_admin` only (mirrors existing `admin.py` pattern)

#### Endpoints

```
GET  /api/v1/admin/audit-trail
     Query: tenant_id, entity_type, actor_id, action,
            date_from (ISO), date_to (ISO), limit (≤200, default 50), offset (default 0)
     Response: List[AuditTrailResponse]
     Header: X-Total-Count: <int>

GET  /api/v1/admin/audit-trail/{id}
     Response: AuditTrailResponse
```

#### Schemas (`backend/app/schemas/audit_trail.py`)

```python
class AuditTrailResponse(BaseModel):
    id: str
    tenant_id: str
    entity_type: str
    entity_id: str
    action: str
    actor_id: str
    actor_role: str | None
    ip_address: str | None
    user_agent: str | None
    request_path: str | None
    payload_before: dict | None
    payload_after: dict | None
    status: str
    error_message: str | None
    created_at: datetime
```

---

## 7. Frontend Wiring

All changes are in existing files — no new components.

| File | Change |
|---|---|
| `frontend/src/api/admin.ts` | Add `fetchAuditTrail(filters)` and `fetchAuditDetail(id)` |
| `frontend/src/hooks/useAudit.ts` | Swap mock for `useQuery` → `fetchAuditTrail`; expose filter state |
| `frontend/src/pages/Admin/AuditLog/AuditLogPage.tsx` | Wire filters (entity_type, actor_id, date_from/to) to query params; pagination; loading/error states |
| `frontend/src/mocks/handlers/audit.ts` | Update MSW handler shape to match `AuditTrailResponse` |

---

## 8. Testing

### Backend

- `test_audit_trail_model.py` — model insert, `to_dict()`, index presence
- `test_audit_service.py` — `emit()` happy path, error suppression, context propagation
- `test_audit_middleware.py` — context set/reset, anonymous fallback
- `test_audit_router.py` — list filters (tenant_id, entity_type, date range), pagination, 403 for non-admin

### Frontend

- Update `mocks/handlers/audit.ts` shape
- Smoke-test `useAudit.ts` with updated mock

### Coverage target: ≥ 85%

---

## 9. New Files

```
backend/app/models/audit_trail.py
backend/app/schemas/audit_trail.py
backend/app/services/audit_service.py
backend/app/core/audit_context.py
backend/app/core/audit_middleware.py
backend/app/routers/audit.py
backend/app/tests/test_audit_trail_model.py
backend/app/tests/test_audit_service.py
backend/app/tests/test_audit_middleware.py
backend/app/tests/test_audit_router.py
docs/superpowers/specs/2026-05-25-audit-design.md
```

## 10. Modified Files

```
backend/app/main.py                          — register audit_middleware + audit router
backend/app/routers/mandate.py              — add audit.emit() calls
backend/app/routers/campaign.py             — add audit.emit() calls
backend/app/routers/creatives.py            — add audit.emit() calls
backend/app/routers/admin.py                — add audit.emit() calls
backend/app/routers/analytics.py            — add audit.emit() calls
backend/app/routers/replanning.py           — add audit.emit() calls
backend/app/routers/report.py               — add audit.emit() calls
frontend/src/api/admin.ts
frontend/src/hooks/useAudit.ts
frontend/src/pages/Admin/AuditLog/AuditLogPage.tsx
frontend/src/mocks/handlers/audit.ts
ntm-sessions.ps1                             — add "audit" to ValidateSet + session block
```

---

## 11. Out of Scope

- Alembic migration file (generated separately)
- Real-time audit stream (WebSocket)
- Audit log export (CSV/PDF)
- Row-level diff for `payload_before`/`payload_after` (UI only shows raw JSON)
