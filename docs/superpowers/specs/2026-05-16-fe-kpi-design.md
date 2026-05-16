# fe-kpi — Design Spec

**Date:** 2026-05-16
**Session:** fe-kpi
**Scope:** Extend the Campaign module with a Go Live confirmation step and a KPI management tab (track actual vs. target, edit targets and thresholds). Add a "View KPIs" drilldown from the Analytics red alerts table.

---

## 1. Status Flow & Routing

### New campaign status

| Status | Meaning |
|---|---|
| `live` | Campaign launched; KPI tracking active |

**Full lifecycle:**
`pending → concepts_ready → confirmed → planned → budget_proposed → approved → creative_generating → creative_ready → live`

### Routes (new child routes of `CampaignDetailPage`)

| Path | Component |
|---|---|
| `/admin/campaigns/:id/golive` | `GoLivePage` |
| `/admin/campaigns/:id/kpis` | `KpisPage` |

### Stepper — 9 steps

```typescript
const STEPS = [
  'Create', 'Concepts', 'Confirmed', 'Plan',
  'Budget', 'Approved', 'Creatives', 'Go Live', 'KPIs'
]

const STATUS_TO_STEP: Record<CampaignStatus, number> = {
  pending: 0,
  concepts_ready: 1,
  confirmed: 2,
  planned: 3,
  budget_proposed: 4,
  approved: 5,
  creative_generating: 6,
  creative_ready: 7,
  live: 8,
}

const STEP_PATHS = [
  null, 'concepts', 'plan', 'plan',
  'budget', 'budget', 'creatives', 'golive', 'kpis'
]
```

### Redirect logic (on base `/admin/campaigns/:id/` load)

| Status | Redirects to |
|---|---|
| `concepts_ready` | `/concepts` |
| `confirmed` \| `planned` | `/plan` |
| `budget_proposed` | `/budget` |
| `approved` \| `creative_generating` | `/creatives` |
| `creative_ready` | `/golive` |
| `live` | `/kpis` |

---

## 2. Data Model

### Types appended to `frontend/src/types/admin.ts`

```typescript
export interface KpiConfig {
  activation_id: string
  kpi_name: string
  unit: string
  target: number
  green_threshold: number  // achievement_percent >= this → green
  amber_threshold: number  // achievement_percent >= this → amber, else red
}

export interface CampaignKpiRow {
  activation_id: string
  channel: string
  sub_channel: string
  kpi_name: string
  unit: string
  target: number
  actual: number
  achievement_percent: number
  green_threshold: number
  amber_threshold: number
  status: 'red' | 'amber' | 'green'
}
```

### Modifications to existing types

**`CampaignStatus`** — add `'live'`:
```typescript
export type CampaignStatus =
  | 'pending' | 'concepts_ready' | 'confirmed'
  | 'planned' | 'budget_proposed' | 'approved'
  | 'creative_generating' | 'creative_ready'
  | 'live'
```

**`Campaign`** — add one new field:
```typescript
kpi_configs: KpiConfig[]
```

---

## 3. MSW — Seed Data & Handlers

### Seed data changes (`frontend/src/mocks/db/campaigns.ts`)

- **c-001, c-002, c-003**: add `kpi_configs: []`
- **New campaign factory** (POST `/campaigns`): add `kpi_configs: []`
- **New seed campaign `c-004`**: `status: 'live'`, `tenant_id: 't1'`, `mandate_id: 'm-002'`, activation plan = `baseActivations`, budget proposal = `baseBudgetProposal`, `kpi_configs` pre-populated from `baseActivations` with defaults (green ≥ 90, amber ≥ 70), creative assets pre-generated

### Seed data changes (`frontend/src/mocks/db/analytics.ts`)

Add a new exported map `kpiActualsDb` keyed by `campaign_id → activation_id → kpi_name → actual (number)`:

```typescript
export const kpiActualsDb: Record<string, Record<string, Record<string, number>>> = {
  'c-004': {
    'act-001': { 'Clicks': 2800, 'CTR': 3.1, 'Conversions': 130 },
    'act-002': { 'Impressions': 72000, 'Engagement Rate': 1.6, 'Lead Gen Forms': 175 },
    'act-003': { 'Reach': 140000, 'ROAS': 3.8 },
  },
}
```

The GET kpis handler imports `kpiActualsDb` from `../db/analytics` and joins it with `campaign.kpi_configs` at request time.

### New MSW handlers (`frontend/src/mocks/handlers/campaigns.ts`)

```
POST /api/v1/campaigns/:id/go-live
  Sets status → 'live'
  Initialises kpi_configs from activation_plan:
    for each activation, for each kpi:
      { activation_id, kpi_name, unit: kpi.unit, target: kpi.target,
        green_threshold: 90, amber_threshold: 70 }
  Returns updated campaign

GET /api/v1/campaigns/:id/kpis
  Imports kpiActualsDb from ../db/analytics
  For each KpiConfig in campaign.kpi_configs:
    actual = kpiActualsDb[campaign.id]?.[config.activation_id]?.[config.kpi_name] ?? 0
    achievement_percent = config.target > 0 ? round((actual / config.target) * 100, 1) : 0
    status = achievement_percent >= config.green_threshold ? 'green'
           : achievement_percent >= config.amber_threshold ? 'amber' : 'red'
    channel/sub_channel from matching activation in campaign.activation_plan
  Returns CampaignKpiRow[]

PATCH /api/v1/campaigns/:id/kpi-configs/:activationId/:kpiName
  Body: { target?, green_threshold?, amber_threshold? }
  Merges patch into matching KpiConfig in campaignStore
  Returns updated campaign
```

---

## 4. React Query Hooks (`frontend/src/hooks/useCampaigns.ts`)

```typescript
// New payload type
export interface UpdateKpiConfigPayload {
  activationId: string
  kpiName: string
  target?: number
  green_threshold?: number
  amber_threshold?: number
}

export function useGoLive(campaignId: string)
  // useMutation — POST go-live
  // onSuccess: invalidate ['campaign', campaignId]

export function useCampaignKpis(campaignId: string)
  // useQuery<CampaignKpiRow[]>
  // queryKey: ['campaign-kpis', campaignId]
  // enabled: !!campaignId

export function useUpdateKpiConfig(campaignId: string)
  // useMutation<void, unknown, UpdateKpiConfigPayload>
  // PATCH kpi-configs/:activationId/:kpiName
  // onSuccess: invalidate ['campaign-kpis', campaignId]
```

### New API client functions (`frontend/src/api/admin.ts`)

```typescript
export const goLive = (id: string) =>
  apiClient.post(`/campaigns/${id}/go-live`).then((r) => r.data)

export const getCampaignKpis = (id: string) =>
  apiClient.get(`/campaigns/${id}/kpis`).then((r) => r.data)

export const updateKpiConfig = (
  id: string,
  activationId: string,
  kpiName: string,
  payload: { target?: number; green_threshold?: number; amber_threshold?: number },
) =>
  apiClient
    .patch(`/campaigns/${id}/kpi-configs/${activationId}/${kpiName}`, payload)
    .then((r) => r.data)
```

---

## 5. GoLivePage (`frontend/src/pages/Admin/Campaigns/GoLivePage.tsx`)

Rendered at `/admin/campaigns/:id/golive` (status `creative_ready`).

- **Summary card**: Campaign ID, selected concept name, total budget (sum of `activation_plan[*].budget` formatted with currency), creative asset count (`copy.length + scripts.length + images.length + audio.length` from `campaign.creative_assets`)
- **"Launch Campaign" button**: triggers `useGoLive` mutation
- While `isPending`: button disabled, spinner + "Launching…"
- On success: query invalidates → `CampaignDetailPage` redirect effect navigates to `/kpis`
- If `isError`: inline error text "Launch failed. Please try again."

---

## 6. KpisPage (`frontend/src/pages/Admin/Campaigns/KpisPage.tsx`)

Rendered at `/admin/campaigns/:id/kpis` (status `live`).

### Table

Uses the existing `<DataTable>` component. Columns:

| Column | Notes |
|---|---|
| Channel | `activation.channel` |
| Sub-channel | `activation.sub_channel` |
| KPI | `kpi_name` |
| Unit | `unit` |
| Target | numeric |
| Actual | numeric |
| Achievement | `achievement_percent`% with colour-tinted text (green/amber/red) |
| Status | `<Badge>` — green / amber / red |
| — | Edit icon button (`<Pencil>` from lucide-react) |

### Edit dialog

shadcn `<Dialog>` (already installed). Opens on edit icon click, pre-filled with current row values:

- **KPI** (read-only label)
- **Target** — `<Input type="number">`
- **Green threshold %** — `<Input type="number">` (achievement % ≥ this = green)
- **Amber threshold %** — `<Input type="number">` (achievement % ≥ this = amber)
- **Save** button — fires `useUpdateKpiConfig` mutation, closes dialog on success
- **Cancel** button — closes dialog, no save

Validation: amber threshold must be < green threshold; both must be between 0–100. Show inline error text if invalid.

### States

- Loading: `<p>Loading…</p>`
- Empty (no KPI rows): `<p>No KPI data available.</p>`
- Error: `<p>Failed to load KPI data.</p>`

---

## 7. Analytics Page Change (`frontend/src/pages/Admin/Analytics/AnalyticsPage.tsx`)

In the red alerts `DataTable`, add a **"View KPIs"** column (or append to the existing actions cell). It renders:

```tsx
<Button variant="ghost" size="sm" onClick={() => navigate(`/admin/campaigns/${alert.campaign_id}/kpis`)}>
  View KPIs
</Button>
```

`alert.campaign_id` is already present in the `RedAlert` type. `useNavigate` is already used on `AnalyticsPage`.

---

## 8. Modified Files Summary

| File | Change |
|---|---|
| `frontend/src/types/admin.ts` | Add `'live'` to `CampaignStatus`, `kpi_configs` to `Campaign`, new `KpiConfig` + `CampaignKpiRow` types |
| `frontend/src/mocks/db/campaigns.ts` | Add `kpi_configs: []` to c-001/002/003 + factory; add c-004 (`live`) with populated configs |
| `frontend/src/mocks/db/analytics.ts` | Add c-004 analytics activations with actuals |
| `frontend/src/mocks/handlers/campaigns.ts` | 3 new handlers: go-live, GET kpis, PATCH kpi-configs |
| `frontend/src/api/admin.ts` | 3 new functions |
| `frontend/src/hooks/useCampaigns.ts` | 1 new payload type + 3 new hooks |
| `frontend/src/pages/Admin/Campaigns/CampaignDetailPage.tsx` | 9-step stepper, updated redirect for `creative_ready` → `/golive` and `live` → `/kpis` |
| `frontend/src/pages/Admin/Campaigns/GoLivePage.tsx` | New file |
| `frontend/src/pages/Admin/Campaigns/KpisPage.tsx` | New file |
| `frontend/src/pages/Admin/Analytics/AnalyticsPage.tsx` | Add "View KPIs" button to red alerts table |
| `frontend/src/App.tsx` | Add `golive` + `kpis` child routes |
| `frontend/src/test/campaigns.test.tsx` | Smoke tests for GoLivePage + KpisPage; update stepper step count to 9 |
