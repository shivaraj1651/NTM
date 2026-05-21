# NTM Gap Closure Design
**Date:** 2026-05-21  
**Status:** Approved

## Group A — Backend Foundations

### Alembic Migrations (6 files, chained)
- `2026_05_21_01` — tenants + roles
- `2026_05_21_02` — user + user_tenant_access
- `2026_05_21_03` — mandate
- `2026_05_21_04` — client + campaign + campaign_concept
- `2026_05_21_05` — activation + activation_platform_mapping + budget
- `2026_05_21_06` — physical_activation_logs + approval_log

Pattern: `op.create_table` + indexes in upgrade, `op.drop_table` in downgrade. Down-rev chain from `2026_05_13_00`.

### docker-compose.yml
Services: ntm-api (FastAPI:8000), ntm-frontend (Nginx:3000), ntm-agent-worker (Celery), ntm-postgres (pg16:5432), ntm-mongo (mongo7:27017), ntm-redis (redis7:6379), ntm-minio (minio:9000/9001). Volumes for postgres-data, mongo-data, redis-data, minio-data. env_file: .env.

## Group B — Backend APIs

### Admin Router (`routers/admin.py`)
- `POST /api/v1/admin/tenants` — create Tenant, platform_admin only
- `GET  /api/v1/admin/tenants` — list Tenants
- `POST /api/v1/admin/users` — create User (assigns tenant + role)
- `PUT  /api/v1/admin/users/{id}/role` — update role_id
- `GET  /api/v1/admin/audit-log?tenant_id=` — paginated ApprovalLog

### Physical Activation Router (`routers/physical_activation.py`)
- `POST /api/v1/activations/{id}/log-physical` — create PhysicalActivationLog record
- `GET  /api/v1/activations/{id}/physical-logs` — list logs for activation

Request body: `actual_run_date`, `proof_urls[]`, `actual_cost`, `vendor_name`, `grp_circulation`, `notes`.

### Google Analytics 4 Tool (`tools/google_analytics.py`)
Class `GoogleAnalyticsTool` wrapping `google-analytics-data` SDK.  
Methods: `get_metrics(activation) -> dict` — returns sessions, users, goal_completions, bounce_rate.  
Config: `GA4_PROPERTY_ID` env var + service account JSON path.

Register admin + physical_activation routers in `routers/__init__.py`.

## Group C — Frontend

### Physical Activation Tracker (`pages/Admin/Campaigns/PhysicalLogPage.tsx`)
- DataTable of existing logs per campaign (activation_id, event_type, channel, payload, logged_at)
- "Log Activation" button opens Dialog with form fields (run_date, actual_cost, vendor_name, grp, notes, proof_urls)
- MSW mock handler in `handlers/campaigns.ts`
- Route: `/admin/campaigns/:id/physical-log`

### KPI/KRA Dashboard (`pages/KPIDashboard/KPIDashboardPage.tsx`)
Top-level page (sidebar link "KPI Dashboard"):
- Mandate selector dropdown
- KPI gauge cards (progress bar + RAG badge, channel + kpi_name + target vs actual + achievement%)
- KRA summary cards (business-level text outcomes)
- Weekly trend sparklines per channel using Recharts `LineChart`
- Red alert list with Replan CTA
- MSW mock handler at `/api/v1/kpi/dashboard`
- Route: `/kpi-dashboard`

## Group D — Eval Tests AGT-06–15

10 files in `backend/tests/agents/`, pattern from `test_eval_agt01.py`:
- Patch `AsyncAnthropic`, return structured mock LLM response
- Assert `ScoreCard.overall >= PASS_THRESHOLD`
- Parametrize over `["mandate_1", "mandate_2", "mandate_3"]`

| File | Agent | Required fields |
|---|---|---|
| test_eval_agt06.py | Creative Director | brief, asset_type, tone, message |
| test_eval_agt07.py | Copywriter | headline, body_copy, cta |
| test_eval_agt08.py | Scriptwriter | script, scenes, duration, production_notes |
| test_eval_agt09.py | Image Generator | prompt, style, dimensions |
| test_eval_agt10.py | Audio Generator | script, voice_config, duration_seconds |
| test_eval_agt11.py | Video Generator | script, scenes, runway_prompt |
| test_eval_agt12.py | Digital Activator | platform, campaign_id, status |
| test_eval_agt13.py | Analytics | activations, red_alerts, summary_by_channel |
| test_eval_agt14.py | Replanning | recommendations, mandate_id |
| test_eval_agt15.py | Report Generator | report_type, mandate_id, generated_at |

## GitHub Actions CI (`.github/workflows/ci.yml`)

Triggers: push + PR to `main`.  
Jobs (parallel after checkout):
1. `lint-backend`: ruff check + mypy
2. `lint-frontend`: tsc --noEmit + eslint
3. `test`: pytest --cov with SQLite (aiosqlite already in requirements.txt)
4. `docker-build`: docker build backend/Dockerfile + frontend/Dockerfile (no push)
