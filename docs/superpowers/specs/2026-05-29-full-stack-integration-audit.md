# Full-Stack Integration — Gap Audit

**Goal:** frontend hits the real backend (no MSW), data persists, agent tasks run for real.
**Date:** 2026-05-29

This audit maps what the frontend calls against what the backend actually serves, and
surfaces the cross-cutting blockers that must be fixed before *any* authenticated call works.

---

## A. Cross-cutting blockers (affect every request)

These are not per-endpoint issues — they break the whole integration until fixed.

### A1. Auth middleware never populates the user (CRITICAL)
`TenantValidationMiddleware` (backend/app/core/middleware.py) reads
`request.state.user` and `request.state.allowed_tenants`, with a comment "set by
FastAPI-Users middleware." **No such middleware exists.** fastapi-users provides the
current user via a *route dependency* (`current_user`), not via request.state. So for
every non-public request, `request.state.user` is `None` → `InvalidTokenException`.
→ The authenticated API is currently unreachable through the middleware.
**Fix:** middleware must decode the JWT itself, load the user + their tenant(s), and set
`request.state.user` / `allowed_tenants` — or move tenant validation into a dependency.

### A2. Frontend never sends `X-Tenant-ID`
`apiClient` (frontend/src/api/client.ts) only attaches `Authorization`. The middleware
rejects any request without `X-Tenant-ID`.
**Fix:** store tenant id at login and attach it as an interceptor header.

### A3. Auth contract mismatch (login/register)
- Frontend: `POST /api/v1/auth/login` JSON `{email,password}` → expects `{token, user:{id,email,role}}`.
- Backend: `POST /api/v1/auth/jwt/login` form `username/password` → returns `{access_token, token_type}`.
- Frontend: `POST /api/v1/auth/register` → **no backend route at all.**
**Fix:** add a real `/auth/login` + `/auth/register` returning the shape the frontend
expects (wrapping fastapi-users), including the user's role + tenant.

### A4. No data seeding
DB starts empty; there is no seed script and no register route. Nothing to log in as,
no tenant, no mandates/campaigns.
**Fix:** seed script for ≥1 tenant + users per role.

### A5. Mongo env var name mismatch
`campaign.py get_db` reads `MONGO_DB_URL`/`MONGO_DB_NAME`; compose sets `MONGODB_URL`.
→ campaign/creative reads hit `localhost` inside the container and fail.
**Fix:** standardize env var names.

---

## B. Per-endpoint gap (frontend call → backend route)

Frontend baseURL = `/api/v1`. ✅ match · ⚠️ mismatch (path/method/shape) · ❌ missing.

### Auth
| Frontend call | Backend | Status |
|---|---|---|
| POST /auth/login | POST /auth/jwt/login (form, diff shape) | ⚠️ |
| POST /auth/register | — | ❌ |
| POST /auth/password-reset/* | exists | ✅ |

### Admin
| Frontend call | Backend | Status |
|---|---|---|
| GET /admin/tenants | GET /admin/tenants | ✅ |
| POST /admin/tenants {name} | POST /admin/tenants | ✅ (verify shape) |
| PATCH /admin/tenants/{id} {is_active} | — | ❌ |
| GET /admin/tenants/{id}/users | — | ❌ |
| POST /admin/tenants/{id}/users | POST /admin/users | ⚠️ path |
| PATCH /admin/users/{id} {is_active} | PUT /admin/users/{id}/role | ⚠️ |
| GET /admin/roles | — | ❌ |
| GET /admin/audit?filters | GET /admin/audit-log | ⚠️ path+params |
| GET /admin/health | — (only /health, /…/creative-director/health) | ❌ |

### Mandates
| Frontend call | Backend | Status |
|---|---|---|
| GET /mandates (list) / ?tenant_id | — (only /{id}) | ❌ list |
| POST /mandates | POST /mandates | ✅ |
| GET /mandates/{id} | ✅ | ✅ |
| GET /mandates/{id}/summary-card | ✅ | ✅ |
| POST /mandates/{id}/confirm | ✅ | ✅ |
| PATCH /mandates/{id} | PUT /mandates/{id} | ⚠️ method |

### Campaigns
| Frontend call | Backend | Status |
|---|---|---|
| GET /campaigns?tenant_id (list) | — (only /{id}) | ❌ list |
| GET /campaigns/{id} | ✅ | ✅ |
| POST /campaigns {mandate_id} | ✅ | ✅ |
| POST /campaigns/{id}/confirm {selected_concept_id} | ✅ (body differs) | ⚠️ shape |
| GET /campaigns/{id}/activation-plan | ✅ | ✅ |
| POST /campaigns/{id}/approve-budget | ✅ | ✅ |
| POST /campaigns/{id}/confirm-budget | ✅ | ✅ |
| POST /campaigns/{id}/generate-creatives | ✅ | ✅ |
| PATCH /campaigns/{id}/creatives/{kind}/{id} | ✅ | ✅ |
| POST /campaigns/{id}/creatives/{kind}/{id}/regenerate | ✅ | ✅ |
| POST /campaigns/{id}/go-live | ✅ | ✅ |
| POST /campaigns/{id}/activate | ✅ (digital_activator) | ✅ |
| GET /campaigns/{id}/kpis | — (analytics has /campaigns/{id}/analytics) | ❌ |
| PATCH /campaigns/{id}/kpi-configs/{actId}/{kpi} | — | ❌ |
| POST /campaigns/{id}/replan | ✅ (replanning) | ✅ |

### Analytics
| Frontend call | Backend | Status |
|---|---|---|
| GET /analytics/summary?tenant_id&date | — (has /analytics/dashboard) | ❌ |
| GET /analytics/trends?tenant_id&days | — | ❌ |

### Creatives / Activations / Physical
| Frontend call | Backend | Status |
|---|---|---|
| GET /activations/{id}/physical-logs | ✅ | ✅ |
| POST /activations/{id}/log-physical | ✅ | ✅ |

### Onboarding / misc
| Frontend call | Backend | Status |
|---|---|---|
| POST /clients (multipart logo) | — | ❌ |
| DELETE /alerts/{id} | — | ❌ |

---

## C. Tally

- ✅ Path-matched: ~17
- ⚠️ Mismatched (path/method/shape): ~6
- ❌ Missing backend routes: ~11
- Plus **response-shape** divergence even on matched paths (frontend types were built to
  MSW handler shapes, not backend `response_model`s) — must be verified per endpoint.
- Plus 5 cross-cutting blockers (§A).

**Conclusion:** the frontend and backend were built to *different contracts*. "Whole app
wired" = fix 5 blockers + add 11 routes + reconcile ~6 mismatches + verify shapes on ~17,
+ a seed script + per-feature manual verification. This is a multi-stage effort, not a
config tweak.

---

## D. Open design decision

**Who is the source of truth for the contract?**
1. **Backend canonical** — adapt frontend `admin.ts`/types to existing backend routes/shapes; add only the genuinely missing backend routes. Backend already has DB models, services, agents.
2. **Frontend canonical** — treat MSW handler shapes as the spec; change backend routes/shapes to match. Larger backend churn.
3. **Hybrid** — backend canonical for shapes; add missing list/auth/onboarding routes; minimal frontend adaptation where backend is clearly right.

Recommended: **(1) Backend canonical**, since the backend is the system that actually
persists data and runs agents.
