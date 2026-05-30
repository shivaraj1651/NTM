# NTM — Testing Guide (full-stack, no mocks)

How to test every component now that the frontend talks to the **real backend** (MSW
mocks are OFF), with real auth, seeded data, and external calls stubbed.

> Windows note: the shell is PowerShell. Use `Invoke-RestMethod` for scripted API calls
> (PowerShell's `curl` is an alias for `Invoke-WebRequest` and behaves differently). The
> easiest API surface is **Swagger at http://localhost:8000/docs**.

---

## 0. One-time setup

```powershell
# from D:\staging\ntm — bring the whole stack up
docker compose up -d

# create all DB tables (no Alembic migrations exist in this repo)
docker exec ntm-api python -m backend.app.scripts.create_tables

# seed roles + tenant + one user per role
docker exec ntm-api python -m backend.app.scripts.seed
```

**Seeded login users** — all password `devpass123`, all in tenant `tenant-acme`:

| Email | Role | Can do |
|-------|------|--------|
| admin@acme.test | platform_admin | everything (admin pages, mandates, campaigns) |
| tenant@acme.test | tenant_admin | mandates, campaigns, users |
| brand@acme.test | brand_manager | mandates, campaigns |
| cmo@acme.test | cmo | mandates, campaigns, analytics |
| creative@acme.test | creative_lead | campaigns, creatives |
| campaign@acme.test | campaign_manager | campaigns (NOT mandates) |
| viewer@acme.test | viewer | read/analytics only |

Every authenticated request needs **two headers**: `Authorization: Bearer <token>` and
`X-Tenant-ID: tenant-acme`.

---

## 1. Infrastructure smoke test

```powershell
docker compose ps        # 9 containers; data stores show (healthy)
```
Checklist:
- [ ] `ntm-postgres`, `ntm-mongo`, `ntm-redis`, `ntm-minio` → healthy
- [ ] `ntm-api` → healthy, `ntm-agent-worker` / `ntm-beat` running, `ntm-flower` up
- [ ] http://localhost:8000/health → `{"status":"ok"}`
- [ ] http://localhost:8000/docs (Swagger) loads
- [ ] http://localhost:5555 (Flower), http://localhost:9001 (MinIO console: `ntm_minio` / `ntm_minio_dev`)

Connectivity:
```powershell
docker exec ntm-postgres pg_isready -U ntm
docker exec ntm-redis redis-cli ping            # PONG
docker exec ntm-postgres psql -U ntm -d ntm -c "\dt"   # 24 tables + alembic_version
```

---

## 2. Backend API testing

### 2.1 Easiest: Swagger (http://localhost:8000/docs)
1. `POST /api/v1/auth/login` → body `{"email":"admin@acme.test","password":"devpass123"}` → copy `token`.
2. Click **Authorize**, paste `Bearer <token>`. For each call also add header `X-Tenant-ID: tenant-acme` (use the "Try it out" header field).
3. Exercise the endpoints in §2.3.

### 2.2 Scripted (PowerShell)
```powershell
$login = Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/v1/auth/login `
  -ContentType application/json -Body '{"email":"admin@acme.test","password":"devpass123"}'
$H = @{ Authorization = "Bearer $($login.token)"; "X-Tenant-ID" = "tenant-acme" }
$login.user      # { id, email, role: platform_admin, tenant_id: tenant-acme }

# protected, RBAC + DB read
Invoke-RestMethod -Uri http://localhost:8000/api/v1/admin/tenants -Headers $H
```

### 2.3 Auth, RBAC & tenant isolation (the security layer)
- [ ] Login good creds → 200 + token; wrong password → 401
- [ ] Protected route **without** `X-Tenant-ID` → 400 (MISSING_TENANT_HEADER)
- [ ] Protected route with a garbage token → 401 (INVALID_TOKEN)
- [ ] `X-Tenant-ID` not belonging to the user → 403 (TENANT_MISMATCH)
- [ ] **RBAC:** login as `viewer@acme.test`, call `GET /api/v1/admin/tenants` → 403
- [ ] **RBAC:** login as `campaign@acme.test`, `POST /api/v1/mandates` → 403 (campaign_manager can't create mandates)

### 2.4 Mandate lifecycle (Postgres) — login as brand@acme.test
```powershell
$b = '{"name":"Spring Launch","client_id":"client-001","objective":"brand_launch","region":"APAC","total_budget":50000,"currency":"USD","start_date":"2026-06-01","end_date":"2026-08-31","countries":["IN","SG"],"competitors":["Rival"]}'
$m = Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/v1/mandates -Headers $H -ContentType application/json -Body $b
```
- [ ] `POST /mandates` → 201, status `draft`, persisted
- [ ] `GET /mandates` → tenant-scoped list contains it
- [ ] `GET /mandates/{id}` → 200
- [ ] `PUT /mandates/{id}` → 200 (update while draft)
- [ ] `POST /mandates/{id}/confirm` → 200
- [ ] `GET /mandates/{id}/summary-card` → 200

### 2.5 Campaign lifecycle (Mongo) — login with a campaign role
- [ ] `POST /campaigns {mandate_id}` → 201
- [ ] `GET /campaigns` → tenant-scoped list
- [ ] `GET /campaigns/{id}` → 200
- [ ] Lifecycle posts: `/confirm`, `/approve-budget`, `/confirm-budget`, `/generate-creatives`, `/go-live`, `/activate`
- [ ] `GET /campaigns/{id}/activation-plan`, `GET /campaigns/{id}/analytics`

### 2.6 Admin & analytics
- [ ] `GET /admin/tenants` (admin) → list incl. Acme
- [ ] `POST /admin/tenants {name}` → 201; `POST /admin/users` → 201
- [ ] `GET /admin/audit-log` → 200
- [ ] `GET /analytics/dashboard`, `/analytics/kpi-status`, `/analytics/channel-performance` → 200

### 2.7 Physical activation
- [ ] `POST /api/v1/activations/{activation_id}/log-physical` → 201
- [ ] `GET /api/v1/activations/{activation_id}/physical-logs` → list

---

## 3. Celery / agent tasks (stubbed — no external spend)

`NTM_STUB_EXTERNAL=1` is set on api + worker, so agent LLM calls and ad-platform
activations return deterministic fixtures.

```powershell
# trigger the mandate-analysis agent on a real mandate id (from §2.4)
docker exec ntm-api python -c "from backend.app.tasks import run_mandate_analysis; print(run_mandate_analysis.delay('<MANDATE_ID>','tenant-acme').id)"
docker logs ntm-agent-worker --tail 20
```
- [ ] Worker log shows `LLM stubbed (NTM_STUB_EXTERNAL)` → `Stored analysis` → `succeeded`
- [ ] Mandate status becomes `analyzed`:
  `docker exec ntm-postgres psql -U ntm -d ntm -t -c "select status from mandates where id='<MANDATE_ID>';"`
- [ ] Analysis stored in Mongo:
  `docker exec ntm-mongo mongosh -u ntm -p ntm_dev --quiet --eval "db.getSiblingDB('ntm').mandate_analyses.countDocuments()"`
- [ ] Flower (http://localhost:5555) → Tasks tab shows the task as SUCCESS
- [ ] Beat: `docker logs ntm-beat` shows the scheduler running

> Known: only `run_mandate_analysis` has the per-invocation-engine fix. Other task
> files (competitive_intel, campaign, analytics, report, replanning, activation) still
> use the cached-engine pattern and may fail on a 2nd invocation — see "Known gaps".

---

## 4. Frontend UI testing (against the real backend)

```powershell
cd D:\staging\ntm\frontend
npm install        # first time only
npm run dev        # http://localhost:5173  (MSW is OFF; calls proxy to :8000)
```
Open http://localhost:5173 and **log in with the real seeded users** (e.g.
`admin@acme.test` / `devpass123`). Open the browser devtools Network tab and confirm
requests go to `localhost` `/api/v1/...` (proxied to :8000) and there is **no** MSW
service worker.

Per-page walkthrough (log in as `admin@acme.test` for full access):
- [ ] **Login** → lands on role home; wrong password shows error; refresh keeps session
- [ ] **RBAC** — log in as each role; menu/pages differ (viewer is read-only; campaign_manager has no mandate-create)
- [ ] **Onboarding wizard** — steps validate, Review shows data, submit completes
- [ ] **Mandates** — list (real), create via form (persists after reload, visible in Postgres), open summary
- [ ] **Campaigns** — list + create; detail tabs: Plan, Budget, Concepts, Creatives, CI Report, KPIs, Go-Live, Physical Log
- [ ] **Creative Studio** — asset list, asset detail
- [ ] **Analytics / KPIs** — charts render from real analytics endpoints
- [ ] **Admin** (platform_admin) — Tenants (list/create real), Users, Roles (static list), Audit log, Health

Degraded-by-design (real backend has no equivalent — expected to be empty/no-op, not crash):
tenant toggle, deactivate user, per-tenant user list, alert dismiss, KPI inline-edit, analytics trends.

---

## 5. Automated test suites

### Backend (pytest, run from repo root)
```powershell
docker exec ntm-api pytest -q          # in container
# or on host:  python -m pytest -q     # (run from D:\staging\ntm)
```
- [ ] ~732 passed. **14 known pre-existing failures** (NOT from the integration work):
  linkedin_ads assertion drift, `media_planner.allocate_by_phase` signature drift,
  config-secret validation test, and Celery `.delay` broker errors in the unit env.
- Single areas: `pytest backend/tests/routers -q`, `pytest backend/tests/integration -q`
- Golden-path integration test: `pytest backend/tests/integration/test_full_stack_smoke.py -q`

### Frontend (vitest)
```powershell
cd frontend
npm test
```
- [ ] 113 passed. **17 known pre-existing failures** (broken `RoleBadge` component,
  a missing routing test helper, and MSW-timing flakiness) — unrelated to the API wiring.
- Typecheck: `npx tsc --noEmit -p tsconfig.app.json` → 0 errors.

---

## 6. Component-by-component matrix

| Component | How to test | Pass criteria |
|---|---|---|
| Postgres | §1 connectivity, §2.4 | tables exist, mandate persists |
| MongoDB | §3 analysis count | analysis doc written |
| Redis / Celery broker | §3 enqueue | task received by worker |
| MinIO | http://localhost:9001 login | console loads |
| Auth + JWT | §2.3 | login 200, bad token 401 |
| Tenant middleware | §2.3 | missing/mismatch 400/403 |
| RBAC | §2.3 | viewer/campaign_mgr 403s |
| Mandate API | §2.4 | full lifecycle 200/201 |
| Campaign API | §2.5 | list + lifecycle |
| Admin/Analytics API | §2.6 | 200s |
| Agent tasks (stubbed) | §3 | succeeded, persisted |
| Beat scheduler | §3 | scheduler running |
| Frontend ↔ backend | §4 | login + data, no MSW |
| Backend suite | §5 | 732 passed |
| Frontend suite | §5 | 113 passed, tsc 0 |

---

## 7. Teardown
```powershell
docker compose down        # stop (keeps data volumes)
docker compose down -v     # stop + WIPE postgres/mongo/redis/minio data
```
After `down -v`, re-run the §0 `create_tables` + `seed` steps.

---

## Known gaps (expected; not test failures to chase)
- Celery per-invocation-engine fix only applied to `mandate_tasks`; propagate to the other task files for multi-task robustness.
- CI auto-chain looks up the mandate in Mongo but mandates live in Postgres → logs "mandate not found".
- `POST /clients` onboarding (logo→MinIO) not implemented.
- 14 backend + 17 frontend pre-existing test failures (listed in §5).
- ⚠️ `.env` contains real third-party API keys committed to the repo — rotate before sharing.
