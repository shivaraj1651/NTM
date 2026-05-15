# Frontend Analytics Dashboard — Design Spec

**Date:** 2026-05-15
**Task:** fe-analytics
**Branch:** feature/TASK-020

---

## Overview

Add an Analytics page to the existing NTM admin SPA. The page lives at `/admin/analytics` and serves two roles:

- **platform_admin** — cross-tenant view with tenant selector, aggregate stats
- **campaign_manager** — tenant-locked view of their own campaign data

The page combines a today-snapshot (RAG summary cards) with historical trend charts (7d / 30d), plus a red alerts table with action buttons (trigger replanning, dismiss). Backend is mocked via MSW for this session.

---

## Architecture

### Route & Navigation

- New route: `/admin/analytics` inside existing `ProtectedRoute` + `AdminLayout`
- New sidebar nav item: "Analytics" (BarChart icon) between Roles and Audit in `Sidebar.tsx`
- No new layouts or route nesting required

### New Files

| File | Purpose |
|---|---|
| `frontend/src/pages/Admin/Analytics/AnalyticsPage.tsx` | Main page component |
| `frontend/src/hooks/useAnalytics.ts` | React Query hooks for summary + trends |

### Modified Files

| File | Change |
|---|---|
| `frontend/src/App.tsx` | Add `/admin/analytics` route |
| `frontend/src/components/Sidebar.tsx` | Add Analytics nav item |
| `frontend/src/mocks/handlers.ts` | Add 4 new MSW handlers |

### Reused

- `DataTable` component (TanStack Table wrapper)
- `PageHeader` component
- `useAuth` Zustand store (role + tenantId)
- `AdminLayout` + `ProtectedRoute`
- Recharts `LineChart` (already installed)
- shadcn `Skeleton`, `toast`, `Badge`, `Card`

---

## Page Layout

```
[ Tenant Selector ]              ← platform_admin only
[ Date Range Toggle: 7d | 30d ]

[ Summary Cards row ]
  Total Mandates | Active Activations | Total Spend | Avg KPI Achievement %

[ Channel Breakdown row ]
  Google Ads card | Meta Ads card | LinkedIn Ads card
  Each: RAG counts (red / amber / green) + total impressions

[ Trend Charts row ]
  Spend over time (LineChart) | Impressions over time (LineChart)

[ Red Alerts Table ]
  Mandate | Channel | Failed KPI | Achievement % | Status | Actions
  Actions: [Trigger Replanning] [Dismiss]
```

---

## Data & State

### MSW Mock Endpoints

| Method | Endpoint | Response |
|---|---|---|
| GET | `/api/v1/analytics/summary?tenant_id=&date=` | `AnalyticsSummary` (see AGT-13 design spec) |
| GET | `/api/v1/analytics/trends?tenant_id=&mandate_id=&days=7\|30` | `{date, spend, impressions}[]` |
| POST | `/api/v1/campaigns/:id/replan` | `{status: "queued", job_id: "..."}` |
| DELETE | `/api/v1/alerts/:id` | `204 No Content` |

### React Query Hooks (`useAnalytics.ts`)

- `useAnalyticsSummary(tenantId: string, date: string)` — today's snapshot, stale after 5 min
- `useAnalyticsTrends(tenantId: string, mandateId: string | null, days: 7 | 30)` — refetches on date toggle

### Local State (`AnalyticsPage`)

| State | Type | Default |
|---|---|---|
| `selectedTenant` | `string` | auth user's `tenantId` (admins can change) |
| `dateRange` | `7 \| 30` | `7` |
| `selectedMandateId` | `string \| null` | `null` (shows aggregate trends) |

### Role Gate

```ts
const { user } = useAuth()
const isAdmin = user.role === 'platform_admin'
// isAdmin → show tenant selector; else use user.tenantId directly
```

Same pattern as `UsersPage.tsx`.

---

## Components

### `AnalyticsPage`
Orchestrates layout, role check, state wiring. Passes props down to sub-components.

### `SummaryCards`
Four `<Card>` components in a responsive grid:
- Total Mandates (count from summary)
- Active Activations (count of activations with status != "no_kpis")
- Total Spend (sum of `metrics.spend` across all activations)
- Avg KPI Achievement % (mean of all `kpi_results.achievement_percent`)

### `ChannelBreakdown`
Three channel cards (google_ads, meta_ads, linkedin_ads) sourced from `summary_by_channel`. Each shows red/amber/green badge counts and total impressions from aggregated metrics.

### `TrendCharts`
Two side-by-side `<LineChart>` from Recharts:
- X-axis: date labels
- Y-axis: spend (left) / impressions (right)
- Date toggle (7d / 30d) triggers `useAnalyticsTrends` refetch

### `AlertsTable`
`DataTable` wrapper with columns: Mandate, Channel, Failed KPI, Achievement %, Status badge, Actions.
- "Trigger Replanning" → `POST /api/v1/campaigns/:id/replan` → success toast
- "Dismiss" → `DELETE /api/v1/alerts/:id` → optimistic removal from table

---

## Error Handling

| Scenario | Handling |
|---|---|
| Query loading | `Skeleton` placeholders in each section |
| Empty summary | "No analytics data for this tenant yet" empty state |
| Replan success | shadcn `toast` — "Replanning queued" |
| Replan failure | shadcn `toast` — "Failed to trigger replanning" |
| Query error | Inline error message per section (not full-page) |

---

## MSW Seed Data

3 mandates × 3 channels with mixed RAG statuses:
- Mandate 1 (Google Ads: green, Meta Ads: amber, LinkedIn: green)
- Mandate 2 (Google Ads: red, Meta Ads: green, LinkedIn: amber)
- Mandate 3 (Google Ads: amber, Meta Ads: red, LinkedIn: green)

Trend data: 30 daily rows per mandate with realistic spend/impressions values.

---

## Constraints

- No backend implementation — all data via MSW mocks
- No unit tests — consistent with existing admin page pattern
- Recharts already installed (`recharts ^3.8.1`) — no new chart library
- Role check uses existing `useAuth` store — no new auth logic
- `AnalyticsSummary` JSON shape defined by AGT-13 design spec — frontend must match exactly
