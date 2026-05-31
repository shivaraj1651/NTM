# Async Campaign Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move campaign concept/plan/budget generation off the synchronous HTTP request and onto background Celery tasks (the pattern AGT-01 mandate analysis already uses), so real LLM calls no longer blow past HTTP timeouts and the full real cycle completes.

**Architecture:** Each lifecycle endpoint sets an intermediate "generating" status and **dispatches** an existing Celery task (`run_concept_generation`/`run_media_planning`/`run_budget_optimization`), returning immediately. The task runs the real agent, writes the result into the Mongo campaign doc, and advances the status. The frontend polls the campaign (like the mandate summary card) while status is a generating state.

**Tech Stack:** FastAPI, Motor (MongoDB campaigns), Celery (per-call async engine pattern), React + TanStack Query, pytest, vitest.

---

## Status model (already in `CampaignStatusEnum` — no new values needed)

`pending` (concepts generating) → `concepts_ready` → `confirmed` (plan generating) → `planned` → `budget_pending` (budget generating) → `budget_proposed` → `approved` → `creative_ready` → `live`.

On agent failure, the task writes an `error` field on the campaign doc and leaves the status at the generating value (frontend shows an error after a timeout). Creatives stay as-is (separate follow-up).

## File structure
- `backend/app/tasks/campaign_tasks.py` — add `run_concept_generation`; make `run_media_planning` set `status="planned"`; confirm `run_budget_optimization` sets `status="budget_proposed"`.
- `backend/app/services/campaign_service.py` — `create`, `confirm`, `get_activation_plan`, `propose_budget` dispatch tasks instead of awaiting agents.
- `backend/app/routers/campaign.py` — unchanged routes; they already call the service methods.
- `frontend/src/hooks/useCampaigns.ts` — poll `useCampaign` while status is a generating state.
- `frontend/src/pages/Admin/Campaigns/{ConceptsPage,PlanPage,BudgetPage}.tsx` — "Generating…" states.
- Tests: `backend/tests/services/test_campaign_service.py`, `backend/tests/test_tasks/`, `frontend/src/test/campaigns.test.tsx`.

---

### Task 1: Concept generation → background task

**Files:** `backend/app/tasks/campaign_tasks.py`, `backend/app/services/campaign_service.py`, tests.

- [ ] **Step 1: Failing test (service.create returns `pending` and dispatches, does NOT call the agent)**

In `backend/tests/services/test_campaign_service.py` (mirror existing mocks of `self._campaigns`/`self._mandates`):
```python
@pytest.mark.asyncio
async def test_create_returns_pending_and_dispatches_concept_task(monkeypatch):
    from backend.app.services import campaign_service as mod
    svc = make_campaign_service(mandate={"_id": "m1", "tenant_id": "t1"})  # helper in this file
    called = {}
    monkeypatch.setattr(mod, "run_concept_generation",
                        type("T", (), {"delay": staticmethod(lambda cid, tid: called.update(cid=cid, tid=tid))}))
    # the agent must NOT be awaited synchronously
    monkeypatch.setattr(mod, "campaign_strategist_agent",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("agent called sync")))
    doc = await svc.create("m1", "t1")
    assert doc["status"] == "pending"
    assert doc["concepts"] == []
    assert called["cid"] == doc["_id"] and called["tid"] == "t1"
```

- [ ] **Step 2: Run it — fails** (`run_concept_generation` not imported; create still calls agent).
Run: `python -m pytest backend/tests/services/test_campaign_service.py -o addopts="" -q`

- [ ] **Step 3: Add `run_concept_generation` task** in `campaign_tasks.py` (campaign-id keyed; writes into the campaign doc):
```python
async def _run_concept_generation(campaign_id: str, tenant_id: str) -> None:
    mongo_client = AsyncIOMotorClient(MONGO_DB_URL)
    try:
        db = mongo_client[MONGO_DB_NAME]
        doc = await db["campaigns"].find_one({"_id": campaign_id, "tenant_id": tenant_id})
        if not doc:
            logger.error("[run_concept_generation] campaign not found: %s", campaign_id)
            return
        mandate = await db["mandates"].find_one({"_id": doc["mandate_id"], "tenant_id": tenant_id}) or {}
        ci_doc = await db["mandate_analyses"].find_one({"mandate_id": doc["mandate_id"], "tenant_id": tenant_id})
        ci_report = ci_doc.get("analysis", {}) if ci_doc else {}
        try:
            output = await campaign_strategist_agent(mandate={k: v for k, v in mandate.items() if k != "_id"},
                                                     ci_report=ci_report)
            concepts = output.get("campaigns", [])
            await db["campaigns"].update_one(
                {"_id": campaign_id, "tenant_id": tenant_id},
                {"$set": {"status": "concepts_ready", "concepts": concepts,
                          "updated_at": datetime.now(timezone.utc).isoformat()}})
            logger.info("[run_concept_generation] %d concepts for %s", len(concepts), campaign_id)
        except Exception as exc:
            logger.error("[run_concept_generation] AGT-03 failed for %s: %s", campaign_id, exc)
            await db["campaigns"].update_one(
                {"_id": campaign_id, "tenant_id": tenant_id},
                {"$set": {"error": f"concept generation failed: {exc}",
                          "updated_at": datetime.now(timezone.utc).isoformat()}})
    finally:
        mongo_client.close()


@shared_task(bind=True, max_retries=2)
def run_concept_generation(self, campaign_id: str, tenant_id: str) -> None:
    logger.info("[run_concept_generation] start campaign_id=%s", campaign_id)
    try:
        asyncio.run(_run_concept_generation(campaign_id, tenant_id))
    except Exception as exc:
        logger.error("[run_concept_generation] error %s: %s", campaign_id, exc)
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
```

- [ ] **Step 4: Rewrite `CampaignService.create`** (in `campaign_service.py`) to dispatch instead of awaiting the agent. Add `from backend.app.tasks.campaign_tasks import run_concept_generation` at top. Replace the body (lines ~206-229) with:
```python
        now = _utc_now()
        doc = {
            "_id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "mandate_id": mandate_id,
            "status": "pending",
            "concepts": [],
            "selected_concept_id": None,
            "activation_plan": None,
            "budget_proposal": None,
            "creative_assets": None,
            "kpi_configs": [],
            "created_at": now,
            "updated_at": now,
        }
        await self._campaigns.insert_one(doc)
        try:
            run_concept_generation.delay(doc["_id"], tenant_id)
        except Exception as exc:  # broker down — log, don't fail the request
            logger.warning("concept task dispatch failed: %s", exc)
        return doc
```
(Leave the mandate-lookup lines above intact; remove the `campaign_strategist_agent` import/await.)

- [ ] **Step 5: Run tests — pass.** Run: `python -m pytest backend/tests/services/test_campaign_service.py -o addopts="" -q`

- [ ] **Step 6: Commit** `git add backend/app/tasks/campaign_tasks.py backend/app/services/campaign_service.py backend/tests/services/test_campaign_service.py && git commit -m "feat(campaign): async concept generation via Celery"` (end message with the two Co-authored-by trailers used in this repo).

---

### Task 2: Plan generation → background task

**Files:** `campaign_service.py`, `campaign_tasks.py`, tests.

- [ ] **Step 1: Failing test** — `confirm` sets `status="confirmed"` and dispatches `run_media_planning`; does not await `media_planner_agent`.
```python
@pytest.mark.asyncio
async def test_confirm_dispatches_media_planning(monkeypatch):
    from backend.app.services import campaign_service as mod
    svc = make_campaign_service(campaign={"_id": "c1", "tenant_id": "t1", "status": "concepts_ready",
                                          "concepts": [{"id": "k1"}]})
    called = {}
    monkeypatch.setattr(mod, "run_media_planning",
                        type("T", (), {"delay": staticmethod(lambda cid, tid: called.update(cid=cid))}))
    doc = await svc.confirm("c1", "k1", "t1")
    assert doc["status"] == "confirmed"
    assert called["cid"] == "c1"
```

- [ ] **Step 2: Run — fails.**

- [ ] **Step 3: Edit `CampaignService.confirm`** — after the `find_one_and_update` that sets `status="confirmed"`, dispatch the task. Add import `from backend.app.tasks.campaign_tasks import run_media_planning`. Insert before `return updated`:
```python
        try:
            run_media_planning.delay(campaign_id, tenant_id)
        except Exception as exc:
            logger.warning("media planning dispatch failed: %s", exc)
```

- [ ] **Step 4: Edit `CampaignService.get_activation_plan`** — make it read-only (the task fills the plan). Replace its body (lines ~289-344) with:
```python
    async def get_activation_plan(self, campaign_id: str, tenant_id: str) -> dict:
        return await self.get(campaign_id, tenant_id)
```

- [ ] **Step 5: Edit `run_media_planning`** in `campaign_tasks.py` — set the campaign `status` to `"planned"` and use the selected concept. In its `$set`, add `"status": "planned"` alongside `activation_plan`. (Selected-concept logic already present at lines 118-122.)

- [ ] **Step 6: Run tests — pass. Commit** (`feat(campaign): async media planning via Celery`).

---

### Task 3: Budget generation → background task

**Files:** `campaign_service.py`, `campaign_tasks.py`, tests.

- [ ] **Step 1: Failing test** — `propose_budget` sets `status="budget_pending"` and dispatches `run_budget_optimization`; does not await `budget_optimizer_agent`.
```python
@pytest.mark.asyncio
async def test_propose_budget_dispatches_task(monkeypatch):
    from backend.app.services import campaign_service as mod
    svc = make_campaign_service(campaign={"_id": "c1", "tenant_id": "t1", "status": "planned",
                                          "concepts": [{}], "activation_plan": []})
    called = {}
    monkeypatch.setattr(mod, "run_budget_optimization",
                        type("T", (), {"delay": staticmethod(lambda cid, tid: called.update(cid=cid))}))
    doc = await svc.propose_budget("c1", "t1")
    assert doc["status"] == "budget_pending"
    assert called["cid"] == "c1"
```

- [ ] **Step 2: Run — fails.**

- [ ] **Step 3: Rewrite `CampaignService.propose_budget`** (lines ~350-398) to dispatch instead of awaiting. Add import `from backend.app.tasks.campaign_tasks import run_budget_optimization`. New body:
```python
    async def propose_budget(self, campaign_id: str, tenant_id: str) -> dict:
        doc = await self.get(campaign_id, tenant_id)
        if doc["status"] != "planned":
            raise HTTPException(status_code=409, detail=f"Cannot propose budget from status '{doc['status']}'")
        updated = await self._campaigns.find_one_and_update(
            {"_id": campaign_id, "tenant_id": tenant_id},
            {"$set": {"status": "budget_pending", "updated_at": _utc_now()}},
            return_document=True,
        )
        try:
            run_budget_optimization.delay(campaign_id, tenant_id)
        except Exception as exc:
            logger.warning("budget task dispatch failed: %s", exc)
        return updated
```

- [ ] **Step 4: Align `_run_budget_optimization`** budget read for flat (Postgres-mirrored) mandates — replace the `b = mandate.get("budget", {})` block with:
```python
        b = mandate.get("budget") or {"total_amount": mandate.get("total_budget", 0), "currency": mandate.get("currency", "USD")}
        budget_env = {"total_budget": b.get("total_amount", b.get("total_budget", 0)), "currency": b.get("currency", "USD")}
```
(It already sets `status="budget_proposed"` at line 285 — keep that.)

- [ ] **Step 5: Run tests — pass. Commit** (`feat(campaign): async budget optimization via Celery`).

---

### Task 4: Frontend polling + generating states

**Files:** `frontend/src/hooks/useCampaigns.ts`, the three stage pages, `frontend/src/test/campaigns.test.tsx`.

- [ ] **Step 1: Failing test** — ConceptsPage shows "Generating" while status `pending` (override GET campaign handler, like the existing rich-shape test):
```tsx
it('shows a generating state while concepts are pending', async () => {
  server.use(http.get('/api/v1/campaigns/:id', () =>
    HttpResponse.json({ id: 'c-gen', mandate_id: 'm', tenant_id: 't1', status: 'pending',
      concepts: [], selected_concept_id: null, activation_plan: null, budget_proposal: null,
      creative_assets: null, kpi_configs: [], created_at: '2026-05-31T00:00:00Z', updated_at: '2026-05-31T00:00:00Z' })))
  renderCampaignPage(<ConceptsPage />, 'c-gen')
  expect(await screen.findByText(/generating/i)).toBeInTheDocument()
})
```

- [ ] **Step 2: Run — fails.**

- [ ] **Step 3: Poll in `useCampaign`** (`useCampaigns.ts`) — add `refetchInterval`:
```ts
export function useCampaign(campaignId: string, options?: Partial<UseQueryOptions<Campaign>>) {
  return useQuery<Campaign>({
    queryKey: ['campaign', campaignId],
    queryFn: () => getCampaign(campaignId),
    enabled: !!campaignId,
    refetchInterval: (query) => {
      const s = query.state.data?.status
      return s === 'pending' || s === 'confirmed' || s === 'budget_pending' || s === 'creative_generating' ? 3000 : false
    },
    ...options,
  })
}
```

- [ ] **Step 4: Generating states in the stage pages.** In `ConceptsPage`, after the `if (!campaign) return null` guard:
```tsx
  if (campaign.status === 'pending') return <p className="text-muted-foreground text-sm">Generating concepts…</p>
```
In `PlanPage`, guard for `confirmed`:
```tsx
  if (campaign?.status === 'confirmed') return <p className="text-muted-foreground text-sm">Generating activation plan…</p>
```
In `BudgetPage`, guard for `budget_pending`:
```tsx
  if (campaign?.status === 'budget_pending') return <p className="text-muted-foreground text-sm">Generating budget…</p>
```
Add `'pending' | 'confirmed' | 'budget_pending' | 'creative_generating'` to the `CampaignStatus` type in `frontend/src/types/admin.ts` if not already present.

- [ ] **Step 5: Run `npx vitest run src/test/campaigns.test.tsx` and `npx tsc --noEmit`** — new test passes; failure count not above the pre-existing baseline. **Commit** (`feat(frontend): poll campaign while generating`).

---

### Task 5: Live full-cycle verification

- [ ] **Step 1: Recreate services**: `docker compose up -d ntm-api ntm-agent-worker` (loads code).
- [ ] **Step 2: Drive the cycle** (curl, as `tenant@acme.test`): create mandate → poll analyzed → confirm → `POST /campaigns` returns **immediately** with `status:"pending"` → poll `GET /campaigns/{id}` until `concepts_ready` (concepts populated, real) → `POST /confirm {concept_id}` → poll until `planned` → `POST /approve-budget` → poll until `budget_proposed` → `POST /confirm-budget` → `approved`.
- [ ] **Step 3: Assert** each POST returns in <2s (no timeout), worker logs show each agent succeeding, and the campaign doc accumulates real concepts/plan/budget. Capture a results summary.

---

## Self-Review Notes
- **Spec coverage:** concepts (T1), plan (T2), budget (T3) all moved to tasks; polling (T4); verification (T5). Creatives intentionally out of scope (still stub) — separate follow-up.
- **Type consistency:** task names `run_concept_generation` / `run_media_planning` / `run_budget_optimization` used identically in service dispatch and task defs. Statuses `pending`/`confirmed`/`budget_pending` already exist in `CampaignStatusEnum`.
- **Risk:** `get_activation_plan` becomes read-only — confirm the frontend PlanPage reads the plan from the campaign doc (it does, via `useActivationPlan`/`useCampaign`); the plan is filled by the task on confirm.

## Out of scope (follow-ups)
- Wire real creative agents into `generate_creatives` (currently `_make_stub_creative_assets`).
- Meta Ad Library 400s; LinkedIn/ElevenLabs/GA4 credentials.
- Aligning agent prompts to Pydantic schemas if real concepts fail `CampaignConcept` validation (monitor `validation_errors`/`error` fields after T1).
