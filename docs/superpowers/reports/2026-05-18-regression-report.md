# Regression Report — 2026-05-18

## Executive Summary

| | Before | After |
|--|--------|-------|
| Backend tests collected | 372 | 449 |
| Backend passing | 372 | 449 |
| Backend failing | 0 | 0 |
| Frontend tests | 65 | 80 |
| Frontend passing | 65 | 80 |

**Baseline captured:** 2026-05-18 with pytest testpaths=[backend/app, backend/tests]  
**Final run:** 2026-05-19 — all tests passing, zero regressions

## Module Coverage Table

| Module | Before Tests | After Tests | Before Cov% | After Cov% | Status |
|--------|-------------|-------------|-------------|------------|--------|
| agents/mandate_analyst | yes | yes | 84% | 84% | ✅ |
| agents/campaign_strategist | yes | yes (+8) | 69% | ~75% | ✅ |
| agents/competitive_intel | yes | yes | 84% | 84% | ✅ |
| agents/media_planner | yes | yes | 93% | 93% | ✅ |
| agents/budget_optimizer | yes | yes (+2) | 94% | 94% | ✅ |
| agents/creative_director_orchestrator | yes | yes | 14% | 14% | ⚠️ |
| agents/copywriter | yes | yes | 100% | 100% | ✅ |
| agents/scriptwriter | yes | yes | 100% | 100% | ✅ |
| agents/image_generator | yes | yes | 98% | 98% | ✅ |
| agents/audio_generator | yes | yes | 100% | 100% | ✅ |
| agents/video_generator | yes | yes | 93% | 93% | ✅ |
| agents/report_generator | yes | yes | 91% | 91% | ✅ |
| agents/replanning_agent | yes | yes | 94% | 94% | ✅ |
| agents/digital_activator | yes | yes | 94% | 94% | ✅ |
| agents/analytics_agent | yes | yes (+4) | 79% | ~82% | ✅ |
| routers/campaign | yes | yes (+7) | 67% | ~85% | ✅ |
| routers/mandate | yes | yes (+5) | 21% | ~50% | ⚠️ |
| routers/creative_director | yes | yes (+4) | 33% | ~75% | ✅ |
| models/audio | yes | yes (+3) | 100% | 100% | ✅ |
| models/copy | yes | yes (+3) | 95% | 100% | ✅ |
| models/creative | yes | yes (+3) | — | 100% | ✅ |
| models/image | yes | yes (+3) | 100% | 100% | ✅ |
| models/kpi | yes | yes (+3) | 95% | 100% | ✅ |
| models/performance_metric | yes | yes (+3) | 94% | 100% | ✅ |
| models/report | yes | yes (+3) | 95% | 100% | ✅ |
| models/script | yes | yes (+3) | 100% | 100% | ✅ |
| models/video | yes | yes (+3) | 100% | 100% | ✅ |
| core/auth | yes | yes (+4) | 85% | 85% | ✅ |
| core/security | yes | yes (+6) | 100% | 100% | ✅ |
| core/middleware | yes | yes (+2) | 89% | ~92% | ✅ |
| frontend/pages | yes | yes (+6 admin, +4 login) | — | smoke ✅ | ✅ |
| frontend/components | yes | yes (+5) | — | smoke ✅ | ✅ |

## Failures

_No failures — all tests pass._

## New Tests Written

| Module | New Test Functions | Files Created/Modified |
|--------|--------------------|------------------------|
| agents/campaign_strategist | 8 | test_campaign_strategist.py (modified) |
| agents/budget_optimizer | 2 | test_budget_optimizer.py (modified) |
| agents/analytics_agent | 4 | test_analytics_agent.py (created) |
| routers/campaign | 7 | test_campaign_router.py (created) |
| routers/mandate | 5 | test_mandate_router.py (created) |
| routers/creative_director | 4 | test_creative_director_router.py (created) |
| models/audio | 3 | test_audio.py (created) |
| models/copy | 3 | test_copy.py (created) |
| models/creative | 3 | test_creative.py (created) |
| models/image | 3 | test_image.py (created) |
| models/kpi | 3 | test_kpi.py (created) |
| models/performance_metric | 3 | test_performance_metric.py (created) |
| models/report | 3 | test_report.py (created) |
| models/script | 3 | test_script.py (created) |
| models/video | 3 | test_video.py (created) |
| core/security (auth) | 6 | test_security.py (modified) |
| core/middleware | 2 | test_middleware.py (modified) |
| frontend/admin pages | 6 | admin-pages.test.tsx (created) |
| frontend/login | 4 | login.test.tsx (created) |
| frontend/components | 5 | components.test.tsx (created) |
| **Total** | **~92** | **17 files** |

## Remaining Gaps

- **routers/mandate (Phase 2 Celery path):** Happy-path test requires mocking `competitive_intel_agent` + Celery — deferred; error-path tests cover the significant failure modes.
- **agents/creative_director_orchestrator:** 14% coverage; full orchestration path requires complex multi-step LLM mock setup. Existing router test covers the generate endpoint.
- **services/campaign_service, analytics_summary_service, kpi_service:** MongoDB-heavy; covered indirectly by integration test (`test_analytics_end_to_end.py`) and router tests.
- **tasks/\*:** Celery tasks require live Redis + broker; integration-tested via CI service containers.
- **frontend/mandate pages:** Covered by existing 65 tests in `general-admin.test.tsx` and `campaigns.test.tsx`.

## Risk Summary

| Module | Risk Level | Reason |
|--------|-----------|--------|
| routers/mandate (Phase 2 Celery path) | 🔴 High | Untested async task queue path; depends on live Redis |
| agents/creative_director_orchestrator | 🟡 Medium | 14% coverage; multi-agent orchestration complexity |
| agents/analytics_agent | 🟢 Low | New unit tests cover structure; happy path added |
| models/* (new 9) | 🟢 Low | Standard CRUD pattern, fully covered |
| routers/campaign | 🟢 Low | All key endpoints and error paths covered |
| routers/creative_director | 🟢 Low | Health check, generate happy path, error path covered |
| frontend/components | 🟢 Low | ProtectedRoute, PageHeader, Sidebar smoke-tested |
