# Frontend Campaign Module — Design Spec

**Date:** 2026-05-15
**Session:** fe-campaign
**Branch:** main (new feature branch to be created)

---

## Overview

Add a Campaign module to the NTM admin SPA. Campaign managers and platform admins can list campaigns, create new ones from mandates, and step through the 6-stage lifecycle: concept selection → activation planning → budget approval.

All data is mocked via MSW for this session (no live backend calls).

---

## Campaign Lifecycle

```
pending → concepts_ready → confirmed → planned → budget_proposed → approved
```

| Status | Meaning | Next Action |
|---|---|---|
| `pending` | Campaign being created (agent running) | — |
| `concepts_ready` | 3 concepts generated | User selects a concept |
| `confirmed` | Concept selected | Fetch activation plan |
| `planned` | Activation plan ready | Approve budget |
| `budget_proposed` | Budget optimised | Confirm budget |
| `approved` | Final approved state | — |

---

## Architecture & Routing

New routes nested inside existing `ProtectedRoute` + `AdminLayout`:

```
/campaigns                    → CampaignsPage         (list + create)
/campaigns/:id                → CampaignDetailPage     (smart redirect + stepper)
/campaigns/:id/concepts       → ConceptsPage           (concepts_ready stage)
/campaigns/:id/plan           → PlanPage               (confirmed → planned stage)
/campaigns/:id/budget         → BudgetPage             (budget_proposed → approved stage)
```

**`CampaignDetailPage`** reads `campaign.status` and redirects to the correct sub-page:
- `concepts_ready` → `/concepts`
- `confirmed` | `planned` → `/plan`
- `budget_proposed` | `approved` → `/budget`
- `pending` → show spinner ("Generating concepts…")

**Stepper bar** (rendered by `CampaignDetailPage`, visible on all sub-pages via `<Outlet />`):
```
[Create] → [Concepts] → [Confirm] → [Plan] → [Budget] → [Approved]
```
Completed steps are navigable (read-only). Current step is highlighted.

**Sidebar nav item:** "Campaigns" with `Megaphone` icon from lucide-react, added after Tenants.

---

## New Files

| Action | Path | Responsibility |
|---|---|---|
| Create | `pages/Campaigns/CampaignsPage.tsx` | List table + tenant selector + new campaign dialog |
| Create | `pages/Campaigns/CampaignDetailPage.tsx` | Stepper layout + status-based redirect + `<Outlet />` |
| Create | `pages/Campaigns/ConceptsPage.tsx` | 3 concept cards, select + confirm |
| Create | `pages/Campaigns/PlanPage.tsx` | Activation plan expandable table + approve-budget |
| Create | `pages/Campaigns/BudgetPage.tsx` | Budget summary + confirm-budget |
| Create | `hooks/useCampaigns.ts` | All 8 React Query hooks |
| Create | `mocks/db/campaigns.ts` | Seed data |
| Create | `mocks/handlers/campaigns.ts` | 8 MSW handlers |
| Modify | `mocks/browser.ts` | Register campaign handlers |
| Modify | `types/admin.ts` | Add Campaign, CampaignConcept, Activation, BudgetProposal, Mandate types |
| Modify | `api/admin.ts` | Add 8 API functions |
| Modify | `App.tsx` | Add campaign routes |
| Modify | `components/Sidebar.tsx` | Add Campaigns nav item |

---

## TypeScript Types (additions to `types/admin.ts`)

```typescript
export interface Mandate {
  id: string
  name: string
  tenant_id: string
  budget: { total_budget: number; currency: string }
  geography: { regions: string[]; markets: string[]; country_list: string[] }
  created_at: string
}

export interface CampaignConcept {
  id: string
  name: string
  tagline: string
  channels: string[]
  tone_board: string
  target_audience: string
  risk_flags: { legal: string | null; regulatory: string | null; sensitivity: string | null }
}

export interface Activation {
  id: string
  channel: string
  sub_channel: string
  budget: number
  currency: string
  audience: string
  kpis: { name: string; target: number; unit: string }[]
}

export interface BudgetAllocation {
  channel: string
  amount: number
  percentage: number
}

export interface BudgetProposal {
  total_budget: number
  currency: string
  allocations: BudgetAllocation[]
}

export type CampaignStatus =
  | 'pending'
  | 'concepts_ready'
  | 'confirmed'
  | 'planned'
  | 'budget_proposed'
  | 'approved'

export interface Campaign {
  id: string
  mandate_id: string
  tenant_id: string
  status: CampaignStatus
  concepts: CampaignConcept[]
  selected_concept_id: string | null
  activation_plan: Activation[]
  budget_proposal: BudgetProposal | null
  created_at: string
  updated_at: string
}
```

---

## MSW Mock Endpoints

| Method | Endpoint | Notes |
|---|---|---|
| `GET` | `/api/v1/campaigns?tenant_id=` | Filter by tenant; return `Campaign[]` |
| `POST` | `/api/v1/campaigns` | Body: `{ mandate_id }`; return new `Campaign` at `concepts_ready` |
| `GET` | `/api/v1/campaigns/:id` | Return single `Campaign` |
| `POST` | `/api/v1/campaigns/:id/confirm` | Body: `{ selected_concept_id }`; advance to `confirmed` |
| `GET` | `/api/v1/campaigns/:id/activation-plan` | Advance to `planned`, return campaign with `activation_plan` |
| `POST` | `/api/v1/campaigns/:id/approve-budget` | Advance to `budget_proposed`, return campaign with `budget_proposal` |
| `POST` | `/api/v1/campaigns/:id/confirm-budget` | Advance to `approved` |
| `GET` | `/api/v1/mandates?tenant_id=` | Return `Mandate[]` for new campaign dialog dropdown |

---

## React Query Hooks (`useCampaigns.ts`)

| Hook | Type | Purpose |
|---|---|---|
| `useCampaigns(tenantId)` | `useQuery<Campaign[]>` | List, enabled when tenantId set |
| `useCampaign(campaignId)` | `useQuery<Campaign>` | Single campaign |
| `useCreateCampaign()` | `useMutation` | POST /campaigns, invalidates list |
| `useConfirmConcept(campaignId)` | `useMutation` | POST /confirm, invalidates campaign |
| `useActivationPlan(campaignId, enabled)` | `useQuery<Campaign>` | GET /activation-plan |
| `useApproveBudget(campaignId)` | `useMutation` | POST /approve-budget, invalidates campaign |
| `useConfirmBudget(campaignId)` | `useMutation` | POST /confirm-budget, invalidates campaign |
| `useMandates(tenantId)` | `useQuery<Mandate[]>` | For new campaign dialog |

---

## Page Designs

### CampaignsPage (`/campaigns`)
- Tenant selector (platform_admin only) — same pattern as UsersPage
- `DataTable` columns: Campaign ID (truncated), Mandate name, Status badge, Created At, Actions (View button)
- "New Campaign" button → dialog with mandate dropdown (`useMandates`) + create button
- Status badge colors: `pending`→secondary, `concepts_ready`→outline, `confirmed`→outline-blue, `planned`→outline-blue, `budget_proposed`→outline-amber, `approved`→default (green)

### CampaignDetailPage (`/campaigns/:id`)
- Fetches campaign, renders horizontal stepper, redirects based on status, renders `<Outlet />`
- Stepper maps status to step index:
  - 0 Create, 1 Concepts (`concepts_ready`), 2 Confirmed, 3 Plan (`planned`), 4 Budget (`budget_proposed`), 5 Approved
- Back button → `/campaigns`

### ConceptsPage (`/campaigns/:id/concepts`)
- `PageHeader` with campaign ID
- 3 `<Card>` components — click to expand showing all fields (name, tagline, channels[], tone_board, target_audience, risk_flags)
- Radio-style selection (border highlight on selected card)
- "Confirm Selection" button → `useConfirmConcept` → navigates to `/plan`
- Disabled until a concept is selected

### PlanPage (`/campaigns/:id/plan`)
- On mount: if `status === 'confirmed'`, call `useActivationPlan` to trigger plan generation (GET endpoint)
- Loading state: "Generating activation plan…"
- `DataTable` with expandable rows — each activation row expands to show: channel, sub_channel, budget, currency, audience, KPIs table
- "Approve Budget" button → `useApproveBudget` → navigates to `/budget`

### BudgetPage (`/campaigns/:id/budget`)
- Budget summary `<Card>`: total_budget, currency
- Allocations `DataTable`: channel, amount, percentage
- "Confirm Budget" button → `useConfirmBudget` → refreshes campaign (shows Approved state)
- When `status === 'approved'`: show green "Campaign Approved ✓" banner, hide confirm button

---

## Error Handling

| Scenario | Handling |
|---|---|
| Campaign not found | Redirect to `/campaigns` |
| Sub-page accessed at wrong status | `CampaignDetailPage` redirects to correct sub-page |
| Mutation failure | Inline error text below action button |
| Query loading | "Loading…" text (consistent with existing pages) |
| Concept confirm without selection | Button disabled until selection made |

---

## MSW Seed Data

**Campaigns (tenant `t1`):**
- `c-001`: `concepts_ready` — 3 full concept cards, from mandate `m-001`
- `c-002`: `planned` — activation plan with 4 activations across 3 channels
- `c-003`: `approved` — full campaign with budget proposal confirmed

**Mandates (tenant `t1`):**
- `m-001`: "Q3 Brand Awareness", budget $50,000
- `m-002`: "Product Launch APAC", budget $120,000

---

## Constraints

- No backend calls — all data via MSW
- No unit tests — consistent with existing admin page pattern
- `DataTable` expandable rows: use TanStack Table `getCanExpand` / `row.toggleExpanded()` (already in codebase via `@tanstack/react-table`)
- All routes inside existing `AdminLayout` — no new layout needed
- `CampaignDetailPage` uses nested `<Outlet />` for sub-page rendering
