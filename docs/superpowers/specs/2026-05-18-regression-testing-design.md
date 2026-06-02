---
title: Regression & Comprehensive Testing Design
date: 2026-05-18
task: regression-testing
---

# Regression & Comprehensive Testing Design

## Goal

Run all existing tests, identify coverage gaps, fill them risk-first, and produce a single report documenting before/after state across all modules.

## Scope

### Backend (pytest + coverage)
- `backend/app/agents/` — 16 agents
- `backend/app/routers/` — 3 routers (campaign, mandate, creative_director)
- `backend/app/models/` — 18 SQLAlchemy models
- `backend/app/core/` — auth, config, security, middleware, dependencies, utils
- `backend/app/services/` — platform_config
- `backend/app/tools/` — google_ads, meta_ads
- `backend/app/tasks/` — activation_tasks

### Frontend (vitest + coverage)
- `frontend/src/pages/Admin/Campaigns/` — 7 sub-pages
- `frontend/src/pages/Admin/` — Analytics, AuditLog, Health, Roles, Tenants, Users
- `frontend/src/pages/Mandate/` — MandateForm, Mandates, MandateSummary
- `frontend/src/pages/Onboarding/` — 5 wizard steps
- `frontend/src/pages/Login/`
- `frontend/src/components/` — Sidebar, AdminLayout, ProtectedRoute, data-table, PageHeader

## Phases

### Phase 1: Baseline Triage
Run all existing tests and capture coverage before any changes.

**Backend:**
```
pytest --tb=short -q --cov=backend/app --cov-report=term-missing 2>&1
```
Capture: total collected, passed, failed, error counts; coverage % per file.

**Frontend:**
```
cd frontend && npx vitest run --coverage
```
Capture: test counts, coverage % per file.

Record baseline in report table before writing any new tests.

### Phase 2: Gap Fill (Risk Order)

#### Priority 1 — Agents (16 agents)
Highest risk: complex orchestration, LLM calls, schema-sensitive outputs.

**Strategy per agent:**
- Mock `anthropic.Anthropic` / LLM client with `unittest.mock.patch`
- Test: valid input → expected output schema
- Test: missing/invalid input → raises `ValueError` or returns error state
- Test: LLM returns malformed JSON → agent handles gracefully
- Test: tool call integration (where applicable)

**Agents needing coverage review:**
`mandate_analyst`, `campaign_strategist`, `competitive_intel`, `media_planner`, `budget_optimizer`, `creative_director_orchestrator`, `copywriter`, `scriptwriter`, `image_generator`, `audio_generator`, `video_generator`, `report_generator`, `replanning_agent`, `digital_activator`, `analytics_agent`

#### Priority 2 — Routers (3 routers)
API contract surface; regressions here break the frontend.

**Strategy per router:**
- Use FastAPI `TestClient` with `app.dependency_overrides` for auth and DB session
- Test: happy path returns correct status + schema
- Test: unauthenticated request → 401/403
- Test: invalid payload → 422
- Test: not-found resource → 404
- Test: `tenant_id` isolation (cross-tenant data not accessible)

**Routers:** `campaign.py`, `mandate.py`, `creative_director.py`

#### Priority 3 — Models (18 models)
Lower risk (already covered by TASK-002), but fill constraint and relationship gaps.

**Strategy:**
- Use SQLAlchemy in-memory SQLite (`create_engine("sqlite:///:memory:")` + `Base.metadata.create_all`)
- Test: required fields raise `IntegrityError` when null
- Test: `tenant_id` present on all queries
- Test: relationships load correctly (lazy/eager)
- Test: unique constraints enforced

**Models to review for gaps:** `activation_platform_mapping`, `approval_log`, `physical_activation_log`, `platform_config_template`, `kpi`, `performance_metric`

#### Priority 4 — Core
Auth, security, middleware — security boundary.

**Strategy:**
- Test JWT encode/decode round-trip
- Test expired token rejection
- Test middleware order (auth before business logic)
- Test config validation (missing env vars)
- Test exception handlers return correct HTTP status

#### Priority 5 — Frontend
Expand 4 existing test files; add component tests.

**Strategy:**
- Vitest + React Testing Library + MSW for API mocking
- Test: page renders without crash
- Test: form validation (Zod schemas)
- Test: API success → UI updates
- Test: API error → error state shown
- Test: navigation (route transitions)
- Test: ProtectedRoute redirects unauthenticated users

**Files to expand or create:**
- `campaigns.test.tsx` — add Budget, GoLive, Kpis, Plan, Concepts, Creatives sub-pages
- `mandates.test.tsx` — add MandateForm validation edge cases
- `onboarding.test.tsx` — add BrandGuidelines, Competitors, Review steps
- `general-admin.test.tsx` — add AuditLog, Health, Roles, Tenants, Users pages
- `components.test.tsx` (new) — Sidebar, ProtectedRoute, data-table

### Phase 3: Report Generation

Output file: `docs/superpowers/reports/2026-05-18-regression-report.md`

**Report structure:**
1. **Executive Summary** — overall before/after test counts and coverage %
2. **Module Table** — per-module: before tests, after tests, before coverage %, after coverage %, delta, status (✅ / ⚠️ / ❌)
3. **Failures** — list of any failing tests with file + line + error
4. **New Tests Written** — count per module, files created/modified
5. **Remaining Gaps** — what's still untested and why (out of scope, infra dependency, etc.)
6. **Risk Summary** — which modules still carry highest regression risk

## Constraints

- All new backend tests must use mocks for LLM calls (no real API calls)
- All DB tests must use in-memory SQLite or mock session (no real Postgres)
- All new tests must pass `pytest -q` with zero failures before report is finalized
- Frontend tests use MSW handlers only (no real HTTP calls)
- `tenant_id` must be present in every model query test

## Success Criteria

- All existing passing tests still pass (zero regressions introduced)
- Agent coverage ≥ 70% per agent file
- Router coverage ≥ 80% per router file
- Model coverage ≥ 85% per model file
- Core coverage ≥ 80%
- Frontend: all 5 page groups have at least one test file
- Report file committed to `docs/superpowers/reports/`
