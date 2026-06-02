# Full-Stack Integration — Design Spec

**Goal:** Run NTM as a real full stack — the React frontend hits the live FastAPI
backend (no MSW mocks), data persists in Postgres/Mongo, and agent/Celery tasks execute
end-to-end with external calls stubbed.

**Date:** 2026-05-29
**Companion:** `2026-05-29-full-stack-integration-audit.md` (the gap audit this builds on)

## Decisions (locked)
- **Scope:** whole app wired (all features reachable against the real backend).
- **Source of truth:** **backend canonical.** Adapt the frontend to existing backend
  routes/shapes; add a backend route only when no equivalent exists.
- **External calls:** **fully stubbed/sandboxed** behind one flag. No LLM spend, no real
  ad-platform side effects.
- **Run model:** **Vite dev server (`:5173`)** with MSW off + a dev proxy to the backend.
  The docker `:3000` build is not the test target.

---

## 1. Run topology

```
Browser ──► Vite dev server :5173 ──(proxy /api → :8000)──► FastAPI :8000 (docker)
                                                              ├─ Postgres :5432
                                                              ├─ Mongo :27017
                                                              ├─ Redis :6379
                                                              ├─ MinIO :9000
                                                              └─ Celery worker (NTM_STUB_EXTERNAL=1)
```

- Frontend: `npm run dev`. MSW is gated behind `VITE_USE_MOCKS` (default **off**). Vite
  config gets a `server.proxy` entry: `'/api' → 'http://localhost:8000'` (so the existing
  `baseURL: '/api/v1'` works with no app-code change and no CORS issue).
- Backend + infra + worker: the running docker stack. `NTM_STUB_EXTERNAL=1` is added to
  the `ntm-api` and `ntm-agent-worker` environments.

---

## 2. Decision rule for "backend canonical"

For each frontend call:
1. Backend has an equivalent route → **adapt the frontend** (path/method/type) to it.
2. No equivalent exists → **add a backend route** (tenant-scoped, real persistence).

Routes we will **add** (no backend equivalent): `GET /mandates` (list), `GET /campaigns`
(list), `POST /auth/login` (JSON), `POST /auth/register`, `POST /clients` (onboarding).
Everything else is reconciled by adapting the frontend.

---

## 3. Phases

Each phase is independently verifiable and leaves the app strictly more real.

### P0 — Auth & tenant resolution (the blockers)
The authenticated API is currently unreachable; this phase makes a logged-in,
tenant-scoped request succeed.

**Backend**
- Rework `TenantValidationMiddleware` so it actually authenticates:
  - Read `Authorization: Bearer <jwt>`; decode with the same `JWTStrategy`/secret.
  - Load the user (async DB session) and their allowed tenant ids (primary `tenant_id`
    + `user_tenants` rows).
  - Set `request.state.user`, `request.state.allowed_tenants`, `request.state.tenant_id`,
    and the tenant value used by `get_current_tenant`.
  - Because Starlette `BaseHTTPMiddleware` does not reliably propagate `ContextVar`s set
    in `dispatch` to the endpoint, **`get_current_tenant` is changed to read
    `request.state.tenant_id`** (via `Request`), with the ContextVar kept only as a
    fallback. This is the reliable mechanism.
  - Public paths (no auth/tenant): `/health`, `/docs`, `/openapi.json`, `/redoc`,
    `/api/v1/auth/login`, `/api/v1/auth/register`, `/api/v1/auth/jwt/login`,
    `/api/v1/auth/password-reset/*`.
  - On failure return JSON `{ "detail": ... }` with the right status (401 missing/invalid
    token, 400 missing tenant header, 403 tenant not allowed).
- Add **`POST /api/v1/auth/login`** (JSON `{email,password}`): verify credentials, mint a
  JWT via the strategy, return `{ token, user: { id, email, role, tenant_id } }`.
- Add **`POST /api/v1/auth/register`** (JSON `{email,password[,tenant_id,role]}`): create
  user via fastapi-users manager, return the same shape; 409 on duplicate.
- Fix env mismatch: `campaign.py get_db` (and any sibling) read `MONGODB_URL`/`MONGODB_DB`
  to match compose.

**Frontend**
- `apiClient` request interceptor attaches `X-Tenant-ID` from the auth store.
- `useAuthStore` persists `tenantId` (from the login response) alongside `token`/`user`.
- `enableMocking()` in `main.tsx` keys off `import.meta.env.VITE_USE_MOCKS === 'true'`
  instead of `import.meta.env.DEV`; default off.
- `vite.config.ts` proxy `/api → http://localhost:8000`.

**Verify P0:** `POST /auth/login` returns a token; a protected route (e.g.
`GET /api/v1/mandates/{id}`) succeeds with `Authorization` + `X-Tenant-ID`; missing
tenant → 400, bad token → 401, wrong tenant → 403.

### P1 — Seed data
- A seed script (`backend/app/scripts/seed.py`, runnable via
  `docker exec ntm-api python -m backend.app.scripts.seed`):
  - All `UserRole` values as `roles` rows.
  - One tenant `Acme` (fixed id for predictable `X-Tenant-ID`).
  - One user per role using the prefix convention (`admin@`, `tenant@`, `brand@`, `cmo@`,
    `creative@`, `campaign@`, `viewer@`) with a known dev password, all in the seed tenant.
  - One sample mandate (so list/detail pages render immediately).
- Idempotent (safe to re-run).

**Verify P1:** login as `admin@acme.test`; the JWT carries the right role/tenant.

### P2 — Add genuinely-missing routes
- `GET /api/v1/mandates` — list mandates for the current tenant (shape = array of the same
  object `GET /mandates/{id}` returns).
- `GET /api/v1/campaigns` — list campaigns for the current tenant.
- `POST /api/v1/clients` — onboarding (multipart: profile fields + logo to MinIO); returns
  a `ClientProfile`. (If onboarding can be deferred, this is the one optional add.)
- (`/auth/register` already added in P0.)

**Verify P2:** list endpoints return seeded rows scoped to the tenant.

### P3 — Reconcile mismatches + verify shapes
Adapt the frontend (`api/admin.ts`, `types/admin.ts`, affected hooks/pages) to the backend:
- `/admin/audit?` → `/admin/audit-log` (+ param names).
- `POST /admin/tenants/{id}/users` → `POST /admin/users`; deactivate via the real route;
  `GET /admin/tenants/{id}/users` and `GET /admin/roles`/`/admin/health` → repoint to the
  backend's actual admin routes, or drop the UI affordance if no backend equivalent and it
  is non-essential (decided per item during implementation, backend-canonical).
- `PATCH /mandates/{id}` → `PUT /mandates/{id}`.
- `confirmConcept` body → backend `CampaignConfirmRequest` shape.
- Analytics: `/analytics/summary` + `/analytics/trends` → backend `/analytics/dashboard`,
  `/analytics/kpi-status`, `/analytics/channel-performance`; adapt the dashboard/KPI hooks
  + chart data mappers to the backend shapes.
- Campaign KPIs: `/campaigns/{id}/kpis` → `/campaigns/{id}/analytics`; drop/adjust
  `kpi-configs` UI if no backend equivalent.
- For every matched endpoint, compare backend `response_model` to the frontend TS type and
  align the type (backend wins).

**Verify P3:** each adapted page loads real data without console/network errors.

### P4 — External-call stub layer
- A single switch `NTM_STUB_EXTERNAL` (read once in a small `external/stubs` helper):
  - LLM clients (Anthropic/OpenAI wrappers used by agents) return deterministic fixtures.
  - Agent tools (google_ads, meta, linkedin, stability, runway, elevenlabs, serpapi)
    short-circuit to fixtures.
  - Digital activation / physical activation tasks record a simulated activation instead
    of calling ad platforms.
- Set `NTM_STUB_EXTERNAL=1` on `ntm-api` and `ntm-agent-worker` in compose.

**Verify P4:** enqueue `run_mandate_analysis.delay()`; worker completes using fixtures,
no outbound external calls, result persisted.

### P5 — End-to-end verification
- Manual per-feature walkthrough on `:5173` against the real backend (login, RBAC by role,
  onboarding, mandates, campaigns + all detail tabs, creative studio, analytics/KPIs,
  admin).
- One integration smoke test for the golden path:
  login → create mandate → run analysis (stubbed) → create campaign → approve budget →
  generate creatives (stubbed) → go-live/activate (stubbed) → read analytics.
- Existing `pytest` and `vitest` suites stay green (update tests touched by P3 type/route
  changes).

---

## 4. Components & boundaries

| Unit | Responsibility | Depends on |
|---|---|---|
| `TenantValidationMiddleware` | Authenticate JWT + resolve/validate tenant; populate request.state | JWTStrategy, User/UserTenant models, DB session |
| `auth_login` / `auth_register` routes | JSON auth returning frontend-shaped payload | fastapi-users manager, JWTStrategy |
| `scripts/seed.py` | Idempotent dev data (roles, tenant, users, sample mandate) | models, password hashing |
| list routes (mandates/campaigns) | Tenant-scoped collection reads | existing services |
| `external/stubs` helper | Single gate for all outbound external calls | env flag |
| `frontend api/admin.ts` + `types/admin.ts` | Real contract to backend | apiClient, backend response models |
| `apiClient` interceptors | Attach Authorization + X-Tenant-ID; 401 handling | auth store |

## 5. Error handling
- Auth/tenant failures: structured JSON `{detail}` with 400/401/403 (frontend already
  redirects to `/login` on 401).
- Backend-canonical type alignment prevents silent `undefined` rendering.
- Stub layer must never fall through to a real call when the flag is on (fail closed).

## 6. Out of scope
- Production auth hardening, secret rotation (flagged separately — `.env` has live keys).
- The docker `:3000` prod build's login path (we standardize on `/auth/login`, which the
  prod build will then also use, but prod build is not the test target here).
- Real external integrations (explicitly stubbed).

## 7. Success criteria
1. With MSW off, logging in on `:5173` against the real backend succeeds and lands on the
   role home.
2. Mandates and campaigns created in the UI persist (visible after reload, present in DB).
3. An agent task triggered from the UI runs through Celery and returns a result (stubbed),
   visible in the UI.
4. Every primary page loads real, tenant-scoped data with no network/console errors.
5. `pytest` and `vitest` suites pass.
