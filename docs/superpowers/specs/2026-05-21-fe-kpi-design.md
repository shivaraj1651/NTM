# fe-kpi: Tenant KPI Dashboard Design

**Date:** 2026-05-21
**Scope:** New standalone `/admin/kpi` page with two explicit sections — Business KRAs and Campaign KPIs. Does not modify the existing campaign-scoped `KpisPage`.

---

## Context

`KpisPage.tsx` at `/admin/campaigns/:id/kpis` is a campaign-scoped table — well built, unchanged.
The PRD requires a tenant-level view tracking business commitments (KRAs) and aggregate channel performance (KPIs) across all campaigns.

---

## Two-Section Split

The PRD defines two distinct tracking levels:

| Section | What | Who reads it | Data source |
|---------|------|--------------|-------------|
| **Business KRAs** | Commitments made to client — "500 leads", "20% awareness" | CMO, client | Mandate objectives + aggregate actuals |
| **Campaign KPIs** | Channel execution metrics — CTR, ROAS, impressions per activation | Campaign manager | `analyticsSummaries` activations |

These are different concepts, different audiences, different data shapes.

---

## Files Created / Modified

**New:**
- `frontend/src/pages/Admin/Kpi/KpiDashboardPage.tsx`
- `frontend/src/mocks/db/kpi.ts` — KRA mock data
- `frontend/src/mocks/handlers/kpi.ts` — new endpoints

**Modified:**
- `frontend/src/App.tsx` — add `/admin/kpi` route
- `frontend/src/components/Sidebar.tsx` — add "KPI Dashboard" nav entry
- `frontend/src/hooks/useCampaigns.ts` — add `useKpiDashboard` hook
- `frontend/src/types/admin.ts` — add KRA types

---

## Page Layout

```
/admin/kpi
│
├── [RAG Alert Bar]  — Red: N | Amber: N | Green: N  (aggregate across all campaigns)
│
├── Section 1: Business KRAs
│   ├── KRA row: "Generate 500 Leads in Hyderabad"  [====70%====] 350/500  [AMBER]
│   ├── KRA row: "Increase Brand Awareness by 20%"  [========85%] 17%/20%  [GREEN]
│   └── KRA row: "Reduce Competitor Share by 5%"    [==30%======] 1.5%/5%  [RED]
│
├── Section 2: Campaign KPIs
│   ├── 30-Day Trend Chart (Spend + Impressions line chart)
│   └── Campaign Breakdown Table
│       ├── Campaign | Channel | CTR | ROAS | Spend | Status | →
│       └── Row click → /admin/campaigns/:id/kpis
```

---

## New Types (`admin.ts`)

```typescript
interface BusinessKra {
  kra_id: string
  description: string         // "Generate 500 leads in Hyderabad"
  metric: string              // "leads"
  target: number              // 500
  actual: number              // 350
  unit: string                // "leads" | "%" | "share_points"
  achievement_percent: number // 70.0
  status: 'red' | 'amber' | 'green'
}

interface KpiDashboardData {
  kras: BusinessKra[]
  rag_summary: { red: number; amber: number; green: number }
  campaign_breakdown: CampaignKpiSummary[]
  trends: TrendPoint[]        // reuses existing TrendPoint type
}

interface CampaignKpiSummary {
  campaign_id: string
  mandate_id: string
  channels: string[]
  total_spend: number
  overall_status: 'red' | 'amber' | 'green'
  top_kpi: string             // e.g. "CTR: 3.1%"
}
```

---

## Section 1: Business KRAs

Component: `KraSectionPage` (inside `KpiDashboardPage.tsx`)

Each KRA rendered as a row:
- Left: description label
- Center: progress bar (`actual / target`, width = `achievement_percent %`)
  - Bar color: green ≥ green_threshold, amber ≥ amber_threshold, red below
- Right: `actual / target unit` + RAG badge
- No edit controls (KRAs are mandate-level commitments, not editable here)

Mock KRA data: 3–4 rows covering leads, awareness, competitor share — stored in `mocks/db/kpi.ts`.

---

## Section 2: Campaign KPIs

### 30-Day Trend Chart
- Uses `analyticsTrends` (already in `mocks/db/analytics.ts`)
- Two lines: Spend (left axis), Impressions (right axis)
- Uses `recharts` (confirmed present — `AnalyticsPage.tsx` already imports it)
- Component: `KpiTrendChart` extracted to same file

### Campaign Breakdown Table
- Uses existing `DataTable` component
- Columns: Campaign, Channels (badge list), Top KPI, Total Spend, Status (RAG badge), Link (→ icon)
- Link cell navigates to `/admin/campaigns/:campaign_id/kpis`
- Data from `analyticsSummaries` aggregated per campaign

---

## RAG Alert Bar

Top of page. Three colored stat chips:
- `Red: N campaigns` — links to filtered table view (just highlights red rows)
- `Amber: N campaigns`
- `Green: N campaigns`

Computed from `rag_summary` in `KpiDashboardData`.

---

## New Endpoint + Hook

```
GET /api/v1/kpi/dashboard  →  KpiDashboardData
```

Hook: `useKpiDashboard()` extracted to a new `frontend/src/hooks/useKpi.ts` (keeps campaign hooks focused).

Mock handler: `mocks/handlers/kpi.ts` returns static `KpiDashboardData` assembled from existing mock stores.

---

## Sidebar Entry

Added to `Sidebar.tsx` under the Analytics section:
```
Analytics         (/admin/analytics)
KPI Dashboard     (/admin/kpi)       ← new
```

---

## Route

```typescript
// App.tsx
import { KpiDashboardPage } from '@/pages/Admin/Kpi/KpiDashboardPage'
{ path: 'kpi', element: <KpiDashboardPage /> }
```

---

## Testing (`frontend/src/test/`)

New file: `kpi-dashboard.test.tsx`
- RAG alert bar renders correct counts
- KRA rows render description, progress bar, status badge
- Trend chart renders without error
- Campaign breakdown table links to correct campaign KPI page
- Empty state when no data

---

## What Does NOT Change

- `KpisPage.tsx` — untouched, remains at `/admin/campaigns/:id/kpis`
- `AnalyticsPage.tsx` — untouched
- `analyticsSummaries` mock data — read-only, not mutated
