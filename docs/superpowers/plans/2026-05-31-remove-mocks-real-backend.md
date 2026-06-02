# Remove Mocks / Real Backend Wiring — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every RBAC page talk to the real backend — remove the dead browser-MSW path and replace the frontend "backend route not implemented" stubs (admin tenants/users/roles) with real endpoints.

**Architecture:** The browser already runs with MSW disabled (`VITE_USE_MOCKS=false`); we delete that dead code. The real "fake behavior" lives in `src/api/admin.ts` stubs that return `Promise.resolve()` because the backend route is missing. This plan implements the 4 clean admin endpoints and rewires their stubs. MSW is **kept for the vitest test suite** (per decision). Analytics-trends, alert-dismiss, and KPI-config stubs require new data modeling and are deferred to follow-up plans (see end).

**Tech Stack:** FastAPI + SQLAlchemy async (Postgres), React + TanStack Query + axios, MSW (tests only), pytest, vitest.

---

## Scope

**In scope (this plan):**
- Remove browser MSW dead code (`main.tsx` gate + `src/mocks/browser.ts` + `VITE_USE_MOCKS`).
- Backend: `PATCH /admin/tenants/{id}`, `GET /admin/tenants/{id}/users`, `PATCH /admin/users/{id}`, `GET /admin/roles`.
- Frontend: rewire `toggleTenant`, `getUsersByTenant`, `deactivateUser`, `getRoles` in `src/api/admin.ts`.
- Keep MSW test handlers aligned so the vitest suite stays green.

**Deferred to follow-up plans (need data-model design — DO NOT attempt here):**
- `GET /analytics/trends` — needs day-bucketed aggregation of `analytics_summaries` into `TrendPoint[]`.
- `DELETE /alerts/{id}` — `RedAlert` has no identity; needs an alert-id scheme + a `dismissed_alerts` store + read-path filtering.
- `PATCH /campaigns/{id}/kpi-configs/{activationId}/{kpiName}` — `KPI` model has no `green_threshold`/`amber_threshold` columns; needs a migration.

## File Structure

- `frontend/src/main.tsx` — remove `enableMocking`; render directly.
- `frontend/src/mocks/browser.ts` — **delete** (only `main.tsx` referenced it).
- `frontend/.env` — remove `VITE_USE_MOCKS` line.
- `backend/app/schemas/admin.py` — add `TenantUpdate`, `UserUpdate`, `RoleResponse`; add `role` to `UserResponse`.
- `backend/app/routers/admin.py` — add 4 endpoints.
- `backend/tests/routers/test_admin_router.py` — add endpoint tests (mirror existing patterns in this file).
- `frontend/src/api/admin.ts` — rewire 4 stubs.
- `frontend/src/mocks/handlers/{tenants,users,roles}.ts` — ensure handlers match the (possibly new) routes so vitest stays green.

---

### Task 0: Remove browser MSW dead code

**Files:**
- Modify: `frontend/src/main.tsx`
- Delete: `frontend/src/mocks/browser.ts`
- Modify: `frontend/.env`

- [ ] **Step 1: Replace `main.tsx` with the mock-free bootstrap**

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider } from 'react-router-dom'
import { router } from './App'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </React.StrictMode>
)
```

- [ ] **Step 2: Delete the browser worker file**

Run: `git rm frontend/src/mocks/browser.ts`
(Keep `frontend/src/mocks/handlers/*` and `frontend/src/mocks/db*` — the vitest suite uses them via `src/test/setup.ts`.)

- [ ] **Step 3: Remove `VITE_USE_MOCKS` from `frontend/.env`**

Delete the line `VITE_USE_MOCKS=false`.

- [ ] **Step 4: Verify typecheck + tests + build**

Run: `cd frontend && npx tsc --noEmit && npx vitest run && npx vite build`
Expected: tsc exits 0; vitest passes (pre-existing flakes `loads seeded mandates`, `shows page heading`, `loads all 4 seeded campaigns` excepted); build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/main.tsx frontend/.env
git commit -m "chore(frontend): remove dead browser MSW bootstrap"
```

---

### Task 1: Backend — toggle tenant active (`PATCH /admin/tenants/{id}`)

**Files:**
- Modify: `backend/app/schemas/admin.py`
- Modify: `backend/app/routers/admin.py`
- Test: `backend/tests/routers/test_admin_router.py`

- [ ] **Step 1: Add `TenantUpdate` schema**

In `backend/app/schemas/admin.py`, after `TenantResponse`:

```python
class TenantUpdate(BaseModel):
    is_active: bool
```

- [ ] **Step 2: Write the failing test**

In `backend/tests/routers/test_admin_router.py` (mirror the existing app/dep-override helpers in that file; if absent, mirror `test_clients_router.py`: override `current_user` with a `platform_admin` mock and `get_db` with a mock `AsyncSession`). Add:

```python
def test_toggle_tenant_sets_is_active():
    # arrange: mock session returns an existing tenant
    tenant = MagicMock()
    tenant.id = "t-1"; tenant.name = "Acme"; tenant.is_active = True
    tenant.created_at = datetime(2026, 1, 1)
    session = make_admin_session(scalar=tenant)   # helper in this file
    app = make_admin_app(session)                 # helper in this file (platform_admin)
    client = TestClient(app)
    resp = client.patch("/api/v1/admin/tenants/t-1", json={"is_active": False})
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False
    session.commit.assert_awaited()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest backend/tests/routers/test_admin_router.py::test_toggle_tenant_sets_is_active -o addopts="" -q`
Expected: FAIL (404/405 — route not defined).

- [ ] **Step 4: Implement the endpoint**

In `backend/app/routers/admin.py` add `TenantUpdate` to the schema import and add:

```python
@router.patch("/tenants/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    body: TenantUpdate,
    _: User = Depends(require_role([UserRole.PLATFORM_ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant.is_active = body.is_active
    await db.commit()
    await db.refresh(tenant)
    return TenantResponse(
        id=tenant.id, name=tenant.name,
        is_active=tenant.is_active, created_at=tenant.created_at.isoformat(),
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest backend/tests/routers/test_admin_router.py::test_toggle_tenant_sets_is_active -o addopts="" -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/admin.py backend/app/routers/admin.py backend/tests/routers/test_admin_router.py
git commit -m "feat(admin): PATCH /admin/tenants/{id} to toggle is_active"
```

---

### Task 2: Backend — list users for a tenant (`GET /admin/tenants/{id}/users`)

**Files:**
- Modify: `backend/app/schemas/admin.py`
- Modify: `backend/app/routers/admin.py`
- Test: `backend/tests/routers/test_admin_router.py`

- [ ] **Step 1: Add `role` to `UserResponse`**

In `backend/app/schemas/admin.py`, change `UserResponse`:

```python
class UserResponse(BaseModel):
    id: str
    email: str
    tenant_id: str
    is_active: bool
    role: Optional[str] = None   # role name, for the Users table
    created_at: str

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Write the failing test**

```python
def test_list_users_by_tenant_returns_users_with_role():
    u = MagicMock()
    u.id = "u-1"; u.email = "a@b.com"; u.tenant_id = "t-1"; u.is_active = True
    u.created_at = datetime(2026, 1, 1)
    role = MagicMock(); role.name = "brand_manager"; u.role = role
    session = make_admin_session(scalars=[u])    # helper returns .scalars().all() == [u]
    app = make_admin_app(session)
    client = TestClient(app)
    resp = client.get("/api/v1/admin/tenants/t-1/users")
    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["email"] == "a@b.com"
    assert body[0]["role"] == "brand_manager"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest backend/tests/routers/test_admin_router.py::test_list_users_by_tenant_returns_users_with_role -o addopts="" -q`
Expected: FAIL (route not defined).

- [ ] **Step 4: Implement the endpoint**

In `backend/app/routers/admin.py` add (the `User.role` relationship is eager-safe here because the mock/orm both expose `.role`):

```python
from sqlalchemy.orm import selectinload  # add to imports

@router.get("/tenants/{tenant_id}/users", response_model=list[UserResponse])
async def list_tenant_users(
    tenant_id: str,
    _: User = Depends(require_role([UserRole.PLATFORM_ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> list[UserResponse]:
    result = await db.execute(
        select(User).options(selectinload(User.role)).where(User.tenant_id == tenant_id)
    )
    users = result.scalars().all()
    return [
        UserResponse(
            id=u.id, email=u.email, tenant_id=u.tenant_id,
            is_active=u.is_active,
            role=(u.role.name if u.role else None),
            created_at=u.created_at.isoformat(),
        )
        for u in users
    ]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest backend/tests/routers/test_admin_router.py::test_list_users_by_tenant_returns_users_with_role -o addopts="" -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/admin.py backend/app/routers/admin.py backend/tests/routers/test_admin_router.py
git commit -m "feat(admin): GET /admin/tenants/{id}/users with role name"
```

---

### Task 3: Backend — deactivate/update user (`PATCH /admin/users/{id}`)

**Files:**
- Modify: `backend/app/schemas/admin.py`
- Modify: `backend/app/routers/admin.py`
- Test: `backend/tests/routers/test_admin_router.py`

- [ ] **Step 1: Add `UserUpdate` schema**

```python
class UserUpdate(BaseModel):
    is_active: bool
```

- [ ] **Step 2: Write the failing test**

```python
def test_patch_user_deactivates():
    u = MagicMock()
    u.id = "u-1"; u.email = "a@b.com"; u.tenant_id = "t-1"; u.is_active = True
    u.created_at = datetime(2026, 1, 1); u.role = None
    session = make_admin_session(scalar=u)
    app = make_admin_app(session)
    client = TestClient(app)
    resp = client.patch("/api/v1/admin/users/u-1", json={"is_active": False})
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False
    session.commit.assert_awaited()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest backend/tests/routers/test_admin_router.py::test_patch_user_deactivates -o addopts="" -q`
Expected: FAIL.

- [ ] **Step 4: Implement the endpoint**

Add to `backend/app/routers/admin.py` (import `UserUpdate`):

```python
@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    body: UserUpdate,
    _: User = Depends(require_role([UserRole.PLATFORM_ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    result = await db.execute(
        select(User).options(selectinload(User.role)).where(User.id == user_id)
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    target.is_active = body.is_active
    await db.commit()
    await db.refresh(target)
    return UserResponse(
        id=target.id, email=target.email, tenant_id=target.tenant_id,
        is_active=target.is_active,
        role=(target.role.name if target.role else None),
        created_at=target.created_at.isoformat(),
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest backend/tests/routers/test_admin_router.py::test_patch_user_deactivates -o addopts="" -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/admin.py backend/app/routers/admin.py backend/tests/routers/test_admin_router.py
git commit -m "feat(admin): PATCH /admin/users/{id} to set is_active"
```

---

### Task 4: Backend — list roles with user_count (`GET /admin/roles`)

**Files:**
- Modify: `backend/app/schemas/admin.py`
- Modify: `backend/app/routers/admin.py`
- Test: `backend/tests/routers/test_admin_router.py`

- [ ] **Step 1: Add `RoleResponse` schema**

```python
class RoleResponse(BaseModel):
    id: str
    name: str
    permissions: list[str]
    user_count: int
```

- [ ] **Step 2: Write the failing test**

```python
def test_list_roles_returns_user_counts():
    role = MagicMock(); role.id = "r-1"; role.name = "viewer"; role.permissions = ["view_only"]
    # session.execute called twice: roles list, then count per role
    session = make_admin_session_sequence(
        first_scalars=[role],   # roles
        scalar_values=[3],      # count for role r-1
    )
    app = make_admin_app(session)
    client = TestClient(app)
    resp = client.get("/api/v1/admin/roles")
    assert resp.status_code == 200
    assert resp.json()[0] == {"id": "r-1", "name": "viewer", "permissions": ["view_only"], "user_count": 3}
```

(If `make_admin_session_sequence` is not present, add a small helper in the test file whose `execute` returns queued results in order.)

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest backend/tests/routers/test_admin_router.py::test_list_roles_returns_user_counts -o addopts="" -q`
Expected: FAIL.

- [ ] **Step 4: Implement the endpoint**

Add to `backend/app/routers/admin.py` (import `RoleResponse`, and `from sqlalchemy import func`):

```python
@router.get("/roles", response_model=list[RoleResponse])
async def list_roles(
    _: User = Depends(require_role([UserRole.PLATFORM_ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> list[RoleResponse]:
    result = await db.execute(select(Role).order_by(Role.name))
    roles = result.scalars().all()
    out: list[RoleResponse] = []
    for role in roles:
        count_result = await db.execute(
            select(func.count()).select_from(User).where(User.role_id == role.id)
        )
        user_count = count_result.scalar() or 0
        out.append(RoleResponse(
            id=role.id, name=role.name,
            permissions=list(role.permissions or []),
            user_count=user_count,
        ))
    return out
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest backend/tests/routers/test_admin_router.py::test_list_roles_returns_user_counts -o addopts="" -q`
Expected: PASS.

- [ ] **Step 6: Run the whole admin router test file**

Run: `python -m pytest backend/tests/routers/test_admin_router.py -o addopts="" -q`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/admin.py backend/app/routers/admin.py backend/tests/routers/test_admin_router.py
git commit -m "feat(admin): GET /admin/roles with per-role user_count"
```

---

### Task 5: Frontend — rewire the 4 admin stubs to real endpoints

**Files:**
- Modify: `frontend/src/api/admin.ts`
- Modify (if routes changed): `frontend/src/mocks/handlers/{tenants,users,roles}.ts`
- Test: `frontend/src/test/admin-pages.test.tsx` (existing)

- [ ] **Step 1: Replace the four stubs in `src/api/admin.ts`**

```ts
export const toggleTenant = (id: string, is_active: boolean): Promise<void> =>
  apiClient.patch(`/admin/tenants/${id}`, { is_active }).then(() => undefined)

export const getUsersByTenant = (tenantId: string) =>
  apiClient.get(`/admin/tenants/${tenantId}/users`).then((r) => r.data)

export const deactivateUser = (userId: string): Promise<void> =>
  apiClient.patch(`/admin/users/${userId}`, { is_active: false }).then(() => undefined)

export const getRoles = (): Promise<Role[]> =>
  apiClient.get('/admin/roles').then((r) => r.data)
```

(Remove the now-stale `// backend route not implemented` comments above them. Keep the `Role` import.)

- [ ] **Step 2: Align MSW test handlers**

In `frontend/src/mocks/handlers/tenants.ts`, `users.ts`, `roles.ts`, ensure handlers exist for:
`PATCH /api/v1/admin/tenants/:id`, `GET /api/v1/admin/tenants/:id/users`, `PATCH /api/v1/admin/users/:id`, `GET /api/v1/admin/roles`, returning shapes matching `Tenant`/`User`/`Role` types. (Add any missing handler that mirrors the seed data already in `src/mocks/db`.)

- [ ] **Step 3: Run the admin page tests**

Run: `cd frontend && npx vitest run src/test/admin-pages.test.tsx`
Expected: PASS (no `onUnhandledRequest` warnings for the four routes).

- [ ] **Step 4: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: exit 0.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/admin.ts frontend/src/mocks/handlers
git commit -m "feat(frontend): wire admin tenant/user/role actions to real endpoints"
```

---

### Task 6: Live end-to-end verification (real stack)

- [ ] **Step 1: Confirm stack up**

Run: `docker compose -f docker-compose.yml ps` and `curl.exe http://localhost:8000/health` → `{status: ok}`.

- [ ] **Step 2: Exercise each new endpoint as platform_admin**

Log in (`admin@acme.test`/`devpass123`), then with `Authorization: Bearer <jwt>` + `X-Tenant-ID: tenant-acme`:
- `GET /api/v1/admin/roles` → 200, each role has integer `user_count`.
- `GET /api/v1/admin/tenants/tenant-acme/users` → 200, users include `role`.
- `PATCH /api/v1/admin/tenants/tenant-acme` `{"is_active": false}` → 200, then set back to `true`.
- Create a throwaway user, `PATCH /api/v1/admin/users/{id}` `{"is_active": false}` → 200.

- [ ] **Step 3: UI smoke**

In the browser as `admin@acme.test`: Admin → Tenants (toggle reflects), Users (list loads with role, Deactivate works), Roles (real counts). No console errors.

---

## Self-Review Notes

- **Spec coverage:** Browser-MSW removal ✓ (Task 0). Admin tenants/users/roles ✓ (Tasks 1–5). Analytics-trends / alert-dismiss / KPI-config are **explicitly deferred** below (data-model work).
- **Test-MSW kept** per decision — only `browser.ts` removed.
- **Type consistency:** `UserResponse.role` (backend) ↔ `User.role: string` (frontend) ✓. `RoleResponse{id,name,permissions,user_count}` ↔ `Role` ✓. `TenantResponse` ↔ `Tenant` ✓.

## Follow-up plans required (separate specs — data-model changes)

1. **analytics-trends** — `GET /analytics/trends?mandate_id=&days=` returning `TrendPoint[] = {date, spend, impressions}` by aggregating `analytics_summaries[].activations[].metrics` per date. Needs a small aggregation service + tests.
2. **alert-dismiss** — define a deterministic alert id (e.g. `campaign_id:activation_id:failed_kpi`), add a `dismissed_alerts` Mongo collection, `DELETE /alerts/{id}`, and filter dismissed alerts out of the dashboard/summary read paths. Requires frontend changes in `AnalyticsPage` to send the composite id.
3. **kpi-config** — add `green_threshold`/`amber_threshold` columns to the `KPI` model (Alembic migration), then `PATCH /campaigns/{id}/kpi-configs/{activationId}/{kpiName}` to update target + thresholds; surface real thresholds in `getCampaignKpis`.
