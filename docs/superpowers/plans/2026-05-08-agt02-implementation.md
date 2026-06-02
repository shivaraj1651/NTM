# AGT-02: Competitive Intelligence Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a two-phase competitive intelligence agent that identifies competitors from mandate + client profile, gathers ad intel via SerpAPI + Meta Ad Library, and outputs structured CIReport JSON to MongoDB.

**Architecture:** Phase 1 (sync) uses LLM to identify competitors in <2s and returns job_id. Phase 2 (async Celery task) fetches metrics from SerpAPI + Meta Ad Library (parallelized), caches results (30d profiles, 7d metrics), synthesizes via LLM, and stores final CIReport in MongoDB.

**Tech Stack:** Python 3.12, FastAPI, Anthropic SDK, SerpAPI, Meta Ad Library API, Motor (async MongoDB), Celery, Pydantic v2, pytest with asyncio

---

## File Structure

| File | Responsibility |
|------|-----------------|
| `backend/app/schemas/competitive_intel.py` | Pydantic models: CompetitorIdentity, CompetitorMetrics, CIReportInitial, CIReport |
| `backend/app/tools/serpapi.py` | SerpAPI search wrapper: identify channels, messaging, reach estimates |
| `backend/app/tools/meta_ads.py` | Meta Ad Library lookup: extract spend, placements, audiences |
| `backend/app/agents/competitive_intel.py` | Main agent: Phase 1 (identify_competitors_sync) + Phase 2 (competitive_intel_agent orchestration) |
| `backend/app/tasks/competitive_intel_tasks.py` | Celery task: fetch_competitor_metrics (background metrics gathering + synthesis) |
| `backend/tests/agents/test_competitive_intel.py` | Tests: happy-path Phase 1, error paths |
| `backend/app/routers/mandate.py` | Router integration: POST endpoint to trigger Phase 1 + enqueue Phase 2 |

---

## Tasks

### Task 1: Create Pydantic Schemas
Create `backend/app/schemas/competitive_intel.py` with CompetitorIdentity, ChannelMetrics, CompetitorMetrics, CIReportInitial, WhitespaceOpportunities, CIReport models.

### Task 2: Create SerpAPI Tool
Create `backend/app/tools/serpapi.py` with `search_competitor_ads()` and helper functions to parse channels and messaging themes from search results.

### Task 3: Create Meta Ad Library Tool
Create `backend/app/tools/meta_ads.py` with `lookup_meta_ads()` to query Meta Ad Library endpoint for competitor ads data.

### Task 4: Implement Phase 1 Sync (Competitor Identification)
Create `backend/app/agents/competitive_intel.py` with `identify_competitors_sync()` and `competitive_intel_agent()` entry point for Phase 1 analysis (<2s).

### Task 5: Implement Celery Task for Phase 2 (Metrics Gathering)
Create `backend/app/tasks/competitive_intel_tasks.py` with `fetch_competitor_metrics()` Celery task, caching functions, and LLM synthesis for Phase 2 async analysis.

### Task 6: Router Integration
Modify `backend/app/routers/mandate.py` to add POST endpoint to trigger Phase 1 + enqueue Phase 2, and GET endpoint to poll job status.

### Task 7: Update Settings & Environment Configuration
Add required environment variables to `.env` for SerpAPI, MongoDB, Celery, LLM models.

### Task 8: Test Suite - Integration Test for Phase 1
Add happy-path and error-path tests to `backend/tests/agents/test_competitive_intel.py`.

### Task 9: Documentation & API Schema
Create `docs/TASK-005-agt02-api-reference.md` with endpoint documentation and workflow example.

### Task 10: Final Testing & Verification
Run all tests, verify coverage >80%, check latency targets, lint and type check.

---

## Context for Subagents

- **Current branch:** `feature/IMPL-9`
- **Recent commits:** mandate analyst agent (AGT-01) completed, export components
- **Patterns to follow:** Single LLM call + parsing (from mandate_analyst.py), Celery task pattern, test mocking patterns
- **Database:** MongoDB for ci_reports collection + competitor_cache collection
- **Cache strategy:** 30d profile TTL, 7d metrics TTL, weekly Celery Beat refresh
- **Error handling:** Best-effort output (nulls for missing data, partial reports OK)
- **Testing:** Happy-path tests required, error-path tests recommended
