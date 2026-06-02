# Design: Mandate Cities, Activation Plan Loading, Go Live Real Ads

**Date:** 2026-06-02  
**Status:** Approved

---

## Overview

Three independent improvements to the NTM campaign cycle:

1. **Cities selection in Mandate Form** — after countries are picked, show top cities per country for targeting granularity.
2. **Activation Plan loading state** — show a clear "generating" message while the backend produces the plan; gate the table and Approve Budget button on data arrival.
3. **Go Live synchronous ad activation** — replace Celery async dispatch with direct synchronous API calls to Google Ads and Meta Ads so real campaigns are created immediately on click.

---

## Issue 1: Cities in Mandate Form

### Goal
After a user selects countries in the mandate form, present the top cities for each selected country so they can optionally narrow geographic targeting.

### Data Layer

**`frontend/src/lib/geography.ts`**  
Add a `CITIES` const of type `Record<string, string[]>` — keyed by country name (matching `REGIONS` values), value is 5–8 top cities. Covers all 17 countries in APAC, EMEA, and Americas.

Example shape:
```ts
export const CITIES: Record<string, string[]> = {
  India: ['Mumbai', 'Delhi', 'Bangalore', 'Chennai', 'Hyderabad', 'Pune', 'Kolkata'],
  USA:   ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia'],
  // ...
}
```

### Type Changes

**`frontend/src/types/admin.ts`**  
Add `cities?: string[]` to:
- `Mandate` interface
- `MandateCreate` interface
- `MandateSummaryCard` interface

### Form Changes

**`frontend/src/pages/Mandate/MandateFormPage.tsx`**

- Add `cities` to Zod schema as `z.array(z.string()).optional().default([])`.
- Add `cities: []` to form `defaultValues`.
- When region changes → reset `cities` (already resets `countries`).
- When a country is unchecked → remove any cities that belong to it from the `cities` field value.
- Render a new **Cities** section immediately after the Countries checkboxes, visible when `watchCountries.length > 0`. Groups cities by country with the country name as a sub-label. Each city is a checkbox. Optional — user can skip.

### Mock

`frontend/src/mocks/db/mandates.ts` and `frontend/src/mocks/handlers/mandates.ts` — no special logic; `cities` is an optional passthrough field. Existing create/update handlers already spread the request body.

---

## Issue 2: Activation Plan Loading State

### Goal
After concept confirmation the activation plan is generated asynchronously by AGT-04. The frontend must clearly communicate "generating" state and only show the table and Approve Budget button once data is ready.

### Root Cause
Current `isGenerating = campaign?.status === 'confirmed' && planLoading` only fires during the HTTP request. After the first fetch returns (possibly with empty `activation_plan`), `planLoading` becomes false and the loading state disappears even though the backend Celery task hasn't finished generating the plan.

### Fix

**`frontend/src/pages/Admin/Campaigns/PlanPage.tsx`**

- Change: `const isGenerating = campaign?.status === 'confirmed'`  
  (status-driven, not HTTP-loading-driven — correct semantics)
- Replace the plain `<p>` loading text with a styled card:
  ```
  [spinner]  Please wait, Activation Plan is Generating...
             This may take a few seconds.
  ```
  Use `Loader2` (already imported) + `Card`/`CardContent` from shadcn.
- Wrap the `<Table>` block and `Approve Budget` button in `activations.length > 0` guard — they only render once the plan arrives.
- No changes needed to hooks or polling — `useCampaign` already polls every 3s on `confirmed` status and stops when status becomes `planned`.

---

## Issue 3: Go Live Synchronous Ad Activation

### Goal
When the user clicks "Launch Campaign", real Google Ads and Meta Ads campaigns are created immediately and their IDs are shown in the UI. No Celery dependency for activation.

### Backend Changes

**`backend/app/routers/digital_activator.py`**

Replace the Celery dispatch loop with direct async calls:

```python
from backend.app.tools.google_ads import activate_google
from backend.app.tools.meta_ads import activate_meta

# For each platform in platform_activations:
if platform == "google_ads":
    result = await activate_google(act_payload, base_platform_config, creative_url)
elif platform == "meta_ads":
    result = await activate_meta(act_payload, base_platform_config, creative_url)

final_results[platform] = result
```

After all platforms are activated, write `final_results` to MongoDB:
```python
await db["campaigns"].update_one(
    {"_id": campaign_id, "tenant_id": tenant_id},
    {"$set": {"activation_results": final_results, "updated_at": now}}
)
```

Return a response containing `campaign_id` and `activation_results` (extend response schema or return dict).

**New response shape:**
```python
{
  "job_id": str,
  "campaign_id": str,
  "activation_results": {
    "google_ads": { "campaign_id": "...", "ad_id": "...", "status": "test_live", "test_mode": True, "error": None },
    "meta_ads":   { "campaign_id": "...", "ad_set_id": "...", "ad_id": "...", "status": "test_live", "test_mode": True, "error": None },
  }
}
```

Remove all Celery imports (`platform_activate_google`, `platform_activate_meta`, `platform_activate_linkedin`) from this file.

### Environment

**`.env`** — Add `NTM_ADS_TEST_MODE=1`.  
This creates campaigns as **PAUSED** with a `[TEST]` prefix. No real budget is spent. Platform IDs are real and can be inspected in Google Ads Manager and Meta Ads Manager. Remove this line when ready for production spend.

`NTM_STUB_EXTERNAL` remains unset (default `0`) — real API calls are made.

### Frontend Changes

**`frontend/src/pages/Admin/Campaigns/GoLivePage.tsx`**

- Remove the hardcoded pre-launch warning block:
  ```tsx
  {/* Test mode notice */}
  <div className="...border-amber-300 bg-amber-50...">
    <p className="font-semibold">Developer Test Mode active (NTM_ADS_TEST_MODE=1)</p>
    ...
  </div>
  ```
  This was always shown regardless of actual env state. After activation, the `anyTestMode` badge on the post-launch view (already present) correctly reflects actual test mode from `activation_results[platform].test_mode`.

- No other GoLivePage changes — the post-launch polling and platform cards already work correctly.

### Polling

With synchronous activation, `activation_results` will have final `status: live/test_live/failed` (not `queued`) immediately after the activate call. The `useCampaign` 3s poll will find all platforms resolved on the first fetch after launch, and polling will stop. This is correct behavior.

---

## Files Changed Summary

| File | Change |
|------|--------|
| `frontend/src/lib/geography.ts` | Add `CITIES` const |
| `frontend/src/types/admin.ts` | Add `cities?: string[]` to 3 interfaces |
| `frontend/src/pages/Mandate/MandateFormPage.tsx` | Add cities field + reset logic |
| `frontend/src/pages/Admin/Campaigns/PlanPage.tsx` | Fix isGenerating + loading UI + gate table |
| `frontend/src/pages/Admin/Campaigns/GoLivePage.tsx` | Remove hardcoded test mode warning |
| `backend/app/routers/digital_activator.py` | Synchronous activation, remove Celery dispatch |
| `.env` | Add `NTM_ADS_TEST_MODE=1` |

---

## Out of Scope

- Backend mandate model/schema changes for `cities` (frontend-only for now; backend stores whatever is passed)
- LinkedIn Ads activation (no credentials in env)
- Mandate summary page city display (follow-up)
