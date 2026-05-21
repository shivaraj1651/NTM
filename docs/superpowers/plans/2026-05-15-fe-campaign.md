# Campaign Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Campaign module to the NTM admin SPA supporting a 6-stage lifecycle (pending → concepts_ready → confirmed → planned → budget_proposed → approved) with list, detail, concept selection, activation planning, and budget confirmation pages — all backed by MSW mocks.

**Architecture:** Nested routes under existing `AdminLayout` (`/admin/campaigns/*`) with `CampaignDetailPage` as a layout route rendering a stepper + `<Outlet />` and status-based redirects to the correct sub-page. All data via MSW in-memory mutable store.

**Tech Stack:** React 18, TypeScript, Vite, shadcn/ui, TanStack Query v5, TanStack Table v8 (expandable rows in PlanPage), MSW v2, react-router-dom v7, lucide-react.

---

### Task 1: Campaign Types

**Files:**
- Modify: `frontend/src/types/admin.ts` (append after `TrendPoint` interface)

- [ ] **Step 1: Append campaign types**

Open `frontend/src/types/admin.ts` and append at the end:

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

- [ ] **Step 2: Type-check**

```
cd frontend && npx tsc --noEmit
```
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/admin.ts
git commit -m "[TASK-020] feat: add Campaign, Mandate, Activation, BudgetProposal types"
```

---

### Task 2: MSW Seed Data

**Files:**
- Create: `frontend/src/mocks/db/campaigns.ts`

- [ ] **Step 1: Create mocks/db/campaigns.ts**

```typescript
import type { Campaign, Mandate, CampaignConcept, Activation, BudgetProposal } from '@/types/admin'

const baseConcepts: CampaignConcept[] = [
  {
    id: 'con-001',
    name: 'Bold Futures',
    tagline: 'Lead tomorrow, today.',
    channels: ['Google Ads', 'LinkedIn Ads'],
    tone_board: 'Confident, forward-looking, professional',
    target_audience: 'B2B decision-makers 35–55',
    risk_flags: { legal: null, regulatory: null, sensitivity: null },
  },
  {
    id: 'con-002',
    name: 'Human Connection',
    tagline: 'Where business meets trust.',
    channels: ['Meta Ads', 'Google Ads'],
    tone_board: 'Warm, authentic, community-driven',
    target_audience: 'SME owners 30–50',
    risk_flags: { legal: null, regulatory: 'Financial claims require disclaimer', sensitivity: null },
  },
  {
    id: 'con-003',
    name: 'Data-Driven Edge',
    tagline: 'Smarter decisions. Better results.',
    channels: ['LinkedIn Ads', 'Google Ads', 'Meta Ads'],
    tone_board: 'Analytical, authoritative, results-focused',
    target_audience: 'C-suite executives 40–60',
    risk_flags: { legal: 'Avoid superlative claims', regulatory: null, sensitivity: null },
  },
]

const baseActivations: Activation[] = [
  {
    id: 'act-001',
    channel: 'Google Ads',
    sub_channel: 'Search',
    budget: 12000,
    currency: 'USD',
    audience: 'In-market: B2B software',
    kpis: [
      { name: 'Clicks', target: 3000, unit: 'clicks' },
      { name: 'CTR', target: 3.5, unit: '%' },
      { name: 'Conversions', target: 150, unit: 'leads' },
    ],
  },
  {
    id: 'act-002',
    channel: 'LinkedIn Ads',
    sub_channel: 'Sponsored Content',
    budget: 18000,
    currency: 'USD',
    audience: 'Job title: CTO, CIO — Company size 200+',
    kpis: [
      { name: 'Impressions', target: 80000, unit: 'impressions' },
      { name: 'Engagement Rate', target: 1.8, unit: '%' },
      { name: 'Lead Gen Forms', target: 200, unit: 'leads' },
    ],
  },
  {
    id: 'act-003',
    channel: 'Meta Ads',
    sub_channel: 'Feed',
    budget: 8000,
    currency: 'USD',
    audience: 'Lookalike: existing customers 1%',
    kpis: [
      { name: 'Reach', target: 150000, unit: 'users' },
      { name: 'ROAS', target: 4.2, unit: 'x' },
    ],
  },
  {
    id: 'act-004',
    channel: 'Meta Ads',
    sub_channel: 'Stories',
    budget: 5000,
    currency: 'USD',
    audience: 'Retargeting: website visitors 30d',
    kpis: [
      { name: 'Video Views', target: 20000, unit: 'views' },
      { name: 'Click-Through', target: 2.1, unit: '%' },
    ],
  },
]

const baseBudgetProposal: BudgetProposal = {
  total_budget: 43000,
  currency: 'USD',
  allocations: [
    { channel: 'Google Ads', amount: 12000, percentage: 27.9 },
    { channel: 'LinkedIn Ads', amount: 18000, percentage: 41.9 },
    { channel: 'Meta Ads', amount: 13000, percentage: 30.2 },
  ],
}

const initialCampaigns: Record<string, Campaign> = {
  'c-001': {
    id: 'c-001',
    mandate_id: 'm-001',
    tenant_id: 't1',
    status: 'concepts_ready',
    concepts: baseConcepts,
    selected_concept_id: null,
    activation_plan: [],
    budget_proposal: null,
    created_at: '2026-05-10T09:00:00Z',
    updated_at: '2026-05-10T09:05:00Z',
  },
  'c-002': {
    id: 'c-002',
    mandate_id: 'm-001',
    tenant_id: 't1',
    status: 'planned',
    concepts: baseConcepts,
    selected_concept_id: 'con-001',
    activation_plan: baseActivations,
    budget_proposal: null,
    created_at: '2026-05-08T11:00:00Z',
    updated_at: '2026-05-08T14:30:00Z',
  },
  'c-003': {
    id: 'c-003',
    mandate_id: 'm-002',
    tenant_id: 't1',
    status: 'approved',
    concepts: baseConcepts,
    selected_concept_id: 'con-002',
    activation_plan: baseActivations,
    budget_proposal: baseBudgetProposal,
    created_at: '2026-05-05T10:00:00Z',
    updated_at: '2026-05-12T16:00:00Z',
  },
}

export const campaignStore: Record<string, Campaign> = { ...initialCampaigns }

export const mandates: Mandate[] = [
  {
    id: 'm-001',
    name: 'Q3 Brand Awareness',
    tenant_id: 't1',
    budget: { total_budget: 50000, currency: 'USD' },
    geography: { regions: ['North America'], markets: ['US', 'CA'], country_list: ['United States', 'Canada'] },
    created_at: '2026-04-01T00:00:00Z',
  },
  {
    id: 'm-002',
    name: 'Product Launch APAC',
    tenant_id: 't1',
    budget: { total_budget: 120000, currency: 'USD' },
    geography: { regions: ['Asia Pacific'], markets: ['SG', 'AU', 'JP'], country_list: ['Singapore', 'Australia', 'Japan'] },
    created_at: '2026-04-15T00:00:00Z',
  },
]

export function generateConcepts(mandateId: string): CampaignConcept[] {
  return [
    {
      id: `${mandateId}-con-a`,
      name: 'Market Pioneer',
      tagline: 'First to market, first in mind.',
      channels: ['Google Ads', 'LinkedIn Ads'],
      tone_board: 'Bold, innovative, pioneering',
      target_audience: 'Industry leaders and early adopters',
      risk_flags: { legal: null, regulatory: null, sensitivity: null },
    },
    {
      id: `${mandateId}-con-b`,
      name: 'Trust Builder',
      tagline: 'Reliability you can count on.',
      channels: ['Meta Ads'],
      tone_board: 'Warm, dependable, community-focused',
      target_audience: 'Mainstream buyers seeking reassurance',
      risk_flags: { legal: null, regulatory: null, sensitivity: null },
    },
    {
      id: `${mandateId}-con-c`,
      name: 'ROI Focus',
      tagline: 'Every dollar working harder.',
      channels: ['Google Ads', 'Meta Ads', 'LinkedIn Ads'],
      tone_board: 'Analytical, results-driven, precise',
      target_audience: 'Finance-conscious decision-makers',
      risk_flags: { legal: 'Avoid ROI guarantees', regulatory: null, sensitivity: null },
    },
  ]
}

export function generateActivationPlan(mandateId: string): Activation[] {
  const mandate = mandates.find((m) => m.id === mandateId)
  const total = mandate?.budget.total_budget ?? 50000
  const currency = mandate?.budget.currency ?? 'USD'
  return [
    {
      id: 'act-gen-1',
      channel: 'Google Ads',
      sub_channel: 'Search',
      budget: Math.round(total * 0.3),
      currency,
      audience: 'In-market buyers',
      kpis: [{ name: 'Clicks', target: 2000, unit: 'clicks' }, { name: 'Conversions', target: 100, unit: 'leads' }],
    },
    {
      id: 'act-gen-2',
      channel: 'Meta Ads',
      sub_channel: 'Feed',
      budget: Math.round(total * 0.35),
      currency,
      audience: 'Lookalike: existing customers',
      kpis: [{ name: 'Reach', target: 100000, unit: 'users' }, { name: 'ROAS', target: 3.5, unit: 'x' }],
    },
    {
      id: 'act-gen-3',
      channel: 'LinkedIn Ads',
      sub_channel: 'Sponsored Content',
      budget: Math.round(total * 0.35),
      currency,
      audience: 'Decision-makers at target companies',
      kpis: [{ name: 'Impressions', target: 60000, unit: 'impressions' }, { name: 'Lead Gen Forms', target: 150, unit: 'leads' }],
    },
  ]
}

export function generateBudgetProposal(activations: Activation[]): BudgetProposal {
  const total = activations.reduce((sum, a) => sum + a.budget, 0)
  const currency = activations[0]?.currency ?? 'USD'
  const byChannel: Record<string, number> = {}
  for (const a of activations) {
    byChannel[a.channel] = (byChannel[a.channel] ?? 0) + a.budget
  }
  const allocations = Object.entries(byChannel).map(([channel, amount]) => ({
    channel,
    amount,
    percentage: Math.round((amount / total) * 1000) / 10,
  }))
  return { total_budget: total, currency, allocations }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/mocks/db/campaigns.ts
git commit -m "[TASK-020] feat: add campaign MSW seed data"
```

---

### Task 3: MSW Handlers + Register

**Files:**
- Create: `frontend/src/mocks/handlers/campaigns.ts`
- Modify: `frontend/src/mocks/browser.ts`

- [ ] **Step 1: Create mocks/handlers/campaigns.ts**

```typescript
import { http, HttpResponse } from 'msw'
import * as db from '../db/campaigns'
import type { Campaign } from '@/types/admin'

export const campaignHandlers = [
  http.get('/api/v1/campaigns', ({ request }) => {
    const tenantId = new URL(request.url).searchParams.get('tenant_id')
    const results = Object.values(db.campaignStore).filter(
      (c) => !tenantId || c.tenant_id === tenantId
    )
    return HttpResponse.json(results)
  }),

  http.post('/api/v1/campaigns', async ({ request }) => {
    const { mandate_id } = (await request.json()) as { mandate_id: string }
    const mandate = db.mandates.find((m) => m.id === mandate_id)
    if (!mandate) return new HttpResponse(null, { status: 404 })
    const newId = `c-${Date.now()}`
    const newCampaign: Campaign = {
      id: newId,
      mandate_id,
      tenant_id: mandate.tenant_id,
      status: 'concepts_ready',
      concepts: db.generateConcepts(mandate_id),
      selected_concept_id: null,
      activation_plan: [],
      budget_proposal: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    db.campaignStore[newId] = newCampaign
    return HttpResponse.json(newCampaign, { status: 201 })
  }),

  http.get('/api/v1/campaigns/:id', ({ params }) => {
    const campaign = db.campaignStore[params.id as string]
    if (!campaign) return new HttpResponse(null, { status: 404 })
    return HttpResponse.json(campaign)
  }),

  http.post('/api/v1/campaigns/:id/confirm', async ({ params, request }) => {
    const campaign = db.campaignStore[params.id as string]
    if (!campaign) return new HttpResponse(null, { status: 404 })
    const { selected_concept_id } = (await request.json()) as { selected_concept_id: string }
    db.campaignStore[campaign.id] = {
      ...campaign,
      status: 'confirmed',
      selected_concept_id,
      updated_at: new Date().toISOString(),
    }
    return HttpResponse.json(db.campaignStore[campaign.id])
  }),

  http.get('/api/v1/campaigns/:id/activation-plan', ({ params }) => {
    const campaign = db.campaignStore[params.id as string]
    if (!campaign) return new HttpResponse(null, { status: 404 })
    if (campaign.status === 'confirmed') {
      db.campaignStore[campaign.id] = {
        ...campaign,
        status: 'planned',
        activation_plan: db.generateActivationPlan(campaign.mandate_id),
        updated_at: new Date().toISOString(),
      }
    }
    return HttpResponse.json(db.campaignStore[params.id as string])
  }),

  http.post('/api/v1/campaigns/:id/approve-budget', ({ params }) => {
    const campaign = db.campaignStore[params.id as string]
    if (!campaign) return new HttpResponse(null, { status: 404 })
    db.campaignStore[campaign.id] = {
      ...campaign,
      status: 'budget_proposed',
      budget_proposal: db.generateBudgetProposal(campaign.activation_plan),
      updated_at: new Date().toISOString(),
    }
    return HttpResponse.json(db.campaignStore[campaign.id])
  }),

  http.post('/api/v1/campaigns/:id/confirm-budget', ({ params }) => {
    const campaign = db.campaignStore[params.id as string]
    if (!campaign) return new HttpResponse(null, { status: 404 })
    db.campaignStore[campaign.id] = {
      ...campaign,
      status: 'approved',
      updated_at: new Date().toISOString(),
    }
    return HttpResponse.json(db.campaignStore[campaign.id])
  }),

  http.get('/api/v1/mandates', ({ request }) => {
    const tenantId = new URL(request.url).searchParams.get('tenant_id')
    const results = tenantId
      ? db.mandates.filter((m) => m.tenant_id === tenantId)
      : db.mandates
    return HttpResponse.json(results)
  }),
]
```

- [ ] **Step 2: Register in browser.ts**

In `frontend/src/mocks/browser.ts`, add the import and spread `...campaignHandlers` inside `setupWorker(...)`:

```typescript
import { setupWorker } from 'msw/browser'
import { authHandlers } from './handlers/auth'
import { tenantHandlers } from './handlers/tenants'
import { userHandlers } from './handlers/users'
import { roleHandlers } from './handlers/roles'
import { auditHandlers } from './handlers/audit'
import { healthHandlers } from './handlers/health'
import { analyticsHandlers } from './handlers/analytics'
import { campaignHandlers } from './handlers/campaigns'

export const worker = setupWorker(
  ...authHandlers,
  ...tenantHandlers,
  ...userHandlers,
  ...roleHandlers,
  ...auditHandlers,
  ...healthHandlers,
  ...analyticsHandlers,
  ...campaignHandlers,
)
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/mocks/handlers/campaigns.ts frontend/src/mocks/browser.ts
git commit -m "[TASK-020] feat: add campaign MSW handlers"
```

---

### Task 4: API Client Functions

**Files:**
- Modify: `frontend/src/api/admin.ts` (append at end)

- [ ] **Step 1: Append campaign API functions**

Append to `frontend/src/api/admin.ts`:

```typescript
export const getCampaigns = (tenantId: string) =>
  apiClient.get(`/campaigns?tenant_id=${tenantId}`).then((r) => r.data)

export const getCampaign = (id: string) =>
  apiClient.get(`/campaigns/${id}`).then((r) => r.data)

export const createCampaign = (mandateId: string) =>
  apiClient.post('/campaigns', { mandate_id: mandateId }).then((r) => r.data)

export const confirmConcept = (id: string, selectedConceptId: string) =>
  apiClient
    .post(`/campaigns/${id}/confirm`, { selected_concept_id: selectedConceptId })
    .then((r) => r.data)

export const getActivationPlan = (id: string) =>
  apiClient.get(`/campaigns/${id}/activation-plan`).then((r) => r.data)

export const approveBudget = (id: string) =>
  apiClient.post(`/campaigns/${id}/approve-budget`).then((r) => r.data)

export const confirmBudget = (id: string) =>
  apiClient.post(`/campaigns/${id}/confirm-budget`).then((r) => r.data)

export const getMandates = (tenantId: string) =>
  apiClient.get(`/mandates?tenant_id=${tenantId}`).then((r) => r.data)
```

- [ ] **Step 2: Type-check**

```
cd frontend && npx tsc --noEmit
```
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/admin.ts
git commit -m "[TASK-020] feat: add campaign API client functions"
```

---

### Task 5: React Query Hooks

**Files:**
- Create: `frontend/src/hooks/useCampaigns.ts`

- [ ] **Step 1: Create hooks/useCampaigns.ts**

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getCampaigns,
  getCampaign,
  createCampaign,
  confirmConcept,
  getActivationPlan,
  approveBudget,
  confirmBudget,
  getMandates,
} from '@/api/admin'
import type { Campaign, Mandate } from '@/types/admin'

export function useCampaigns(tenantId: string | null) {
  return useQuery<Campaign[]>({
    queryKey: ['campaigns', tenantId],
    queryFn: () => getCampaigns(tenantId!),
    enabled: !!tenantId,
  })
}

export function useCampaign(campaignId: string) {
  return useQuery<Campaign>({
    queryKey: ['campaign', campaignId],
    queryFn: () => getCampaign(campaignId),
    enabled: !!campaignId,
  })
}

export function useCreateCampaign() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (mandateId: string) => createCampaign(mandateId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['campaigns'] }),
  })
}

export function useConfirmConcept(campaignId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (selectedConceptId: string) => confirmConcept(campaignId, selectedConceptId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['campaign', campaignId] }),
  })
}

export function useActivationPlan(campaignId: string, enabled: boolean) {
  return useQuery<Campaign>({
    queryKey: ['campaign', campaignId, 'activation-plan'],
    queryFn: () => getActivationPlan(campaignId),
    enabled,
  })
}

export function useApproveBudget(campaignId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => approveBudget(campaignId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['campaign', campaignId] }),
  })
}

export function useConfirmBudget(campaignId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => confirmBudget(campaignId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['campaign', campaignId] }),
  })
}

export function useMandates(tenantId: string | null) {
  return useQuery<Mandate[]>({
    queryKey: ['mandates', tenantId],
    queryFn: () => getMandates(tenantId!),
    enabled: !!tenantId,
  })
}
```

- [ ] **Step 2: Type-check**

```
cd frontend && npx tsc --noEmit
```
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/useCampaigns.ts
git commit -m "[TASK-020] feat: add useCampaigns React Query hooks"
```

---

### Task 6: CampaignsPage

**Files:**
- Create: `frontend/src/pages/Admin/Campaigns/CampaignsPage.tsx`

- [ ] **Step 1: Create CampaignsPage.tsx**

```typescript
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { ColumnDef } from '@tanstack/react-table'
import { PageHeader } from '@/components/PageHeader'
import { DataTable } from '@/components/data-table'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useAuthStore } from '@/store/useAuthStore'
import { useTenants } from '@/hooks/useTenants'
import { useCampaigns, useCreateCampaign, useMandates } from '@/hooks/useCampaigns'
import type { Campaign, CampaignStatus } from '@/types/admin'

function statusBadge(status: CampaignStatus) {
  if (status === 'pending') return <Badge variant="secondary">pending</Badge>
  if (status === 'concepts_ready') return <Badge variant="outline">concepts ready</Badge>
  if (status === 'confirmed')
    return <Badge variant="outline" className="border-blue-500 text-blue-600">confirmed</Badge>
  if (status === 'planned')
    return <Badge variant="outline" className="border-blue-500 text-blue-600">planned</Badge>
  if (status === 'budget_proposed')
    return <Badge variant="outline" className="border-amber-500 text-amber-600">budget proposed</Badge>
  return <Badge variant="default">approved</Badge>
}

export function CampaignsPage() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const isAdmin = user?.role === 'platform_admin'

  const { data: tenants = [] } = useTenants()
  const [selectedTenantId, setSelectedTenantId] = useState<string | null>(
    isAdmin ? null : (user?.tenant_id ?? null)
  )
  const [dialogOpen, setDialogOpen] = useState(false)
  const [selectedMandateId, setSelectedMandateId] = useState<string | null>(null)

  const { data: campaigns = [], isLoading } = useCampaigns(selectedTenantId)
  const { data: mandates = [] } = useMandates(selectedTenantId)
  const createCampaign = useCreateCampaign()

  const handleCreate = async () => {
    if (!selectedMandateId) return
    const campaign = await createCampaign.mutateAsync(selectedMandateId)
    setSelectedMandateId(null)
    setDialogOpen(false)
    navigate(`/admin/campaigns/${campaign.id}`)
  }

  const columns: ColumnDef<Campaign>[] = [
    {
      accessorKey: 'id',
      header: 'Campaign ID',
      cell: ({ row }) => (
        <span className="font-mono text-xs">{row.original.id}</span>
      ),
    },
    {
      id: 'mandate',
      header: 'Mandate',
      cell: ({ row }) => {
        const mandate = mandates.find((m) => m.id === row.original.mandate_id)
        return mandate?.name ?? row.original.mandate_id
      },
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => statusBadge(row.original.status),
    },
    {
      accessorKey: 'created_at',
      header: 'Created At',
      cell: ({ row }) => new Date(row.original.created_at).toLocaleDateString(),
    },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => (
        <Button
          variant="outline"
          size="sm"
          onClick={() => navigate(`/admin/campaigns/${row.original.id}`)}
        >
          View
        </Button>
      ),
    },
  ]

  return (
    <div>
      <div className="flex items-start justify-between">
        <PageHeader title="Campaigns" description="Manage campaign lifecycle." />
        <Button onClick={() => setDialogOpen(true)} disabled={!selectedTenantId}>
          New Campaign
        </Button>
      </div>

      {isAdmin && (
        <div className="mb-4 w-56">
          <Select onValueChange={setSelectedTenantId}>
            <SelectTrigger>
              <SelectValue placeholder="Select tenant…" />
            </SelectTrigger>
            <SelectContent>
              {(tenants as { id: string; name: string }[]).map((t) => (
                <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      {!selectedTenantId ? (
        <p className="text-muted-foreground text-sm">Select a tenant to view campaigns.</p>
      ) : isLoading ? (
        <p className="text-muted-foreground text-sm">Loading…</p>
      ) : (
        <DataTable columns={columns} data={campaigns} />
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New Campaign</DialogTitle>
          </DialogHeader>
          <div className="py-2">
            <Select onValueChange={setSelectedMandateId}>
              <SelectTrigger>
                <SelectValue placeholder="Select mandate…" />
              </SelectTrigger>
              <SelectContent>
                {mandates.map((m) => (
                  <SelectItem key={m.id} value={m.id}>
                    {m.name} — {m.budget.currency} {m.budget.total_budget.toLocaleString()}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button
              onClick={handleCreate}
              disabled={!selectedMandateId || createCampaign.isPending}
            >
              {createCampaign.isPending ? 'Creating…' : 'Create'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Admin/Campaigns/CampaignsPage.tsx
git commit -m "[TASK-020] feat: add CampaignsPage with list and create dialog"
```

---

### Task 7: CampaignDetailPage

**Files:**
- Create: `frontend/src/pages/Admin/Campaigns/CampaignDetailPage.tsx`

- [ ] **Step 1: Create CampaignDetailPage.tsx**

```typescript
import { useEffect } from 'react'
import { useParams, useNavigate, useLocation, Outlet, Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useCampaign } from '@/hooks/useCampaigns'
import type { CampaignStatus } from '@/types/admin'
import { cn } from '@/lib/utils'

const STEPS = ['Create', 'Concepts', 'Confirmed', 'Plan', 'Budget', 'Approved']

const STATUS_TO_STEP: Record<CampaignStatus, number> = {
  pending: 0,
  concepts_ready: 1,
  confirmed: 2,
  planned: 3,
  budget_proposed: 4,
  approved: 5,
}

const STEP_PATHS = [null, 'concepts', 'plan', 'plan', 'budget', 'budget']

export function CampaignDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const { data: campaign, isLoading } = useCampaign(id!)

  useEffect(() => {
    if (!campaign) return
    const base = `/admin/campaigns/${id}`
    if (location.pathname !== base && location.pathname !== `${base}/`) return
    const { status } = campaign
    if (status === 'concepts_ready') navigate(`${base}/concepts`, { replace: true })
    else if (status === 'confirmed' || status === 'planned') navigate(`${base}/plan`, { replace: true })
    else if (status === 'budget_proposed' || status === 'approved') navigate(`${base}/budget`, { replace: true })
  }, [campaign, id, navigate, location.pathname])

  if (isLoading) return <p className="text-muted-foreground text-sm">Loading…</p>
  if (!campaign) return null

  const currentStep = STATUS_TO_STEP[campaign.status]
  const base = `/admin/campaigns/${id}`

  return (
    <div>
      <div className="flex items-center gap-4 mb-4">
        <Button variant="outline" size="sm" onClick={() => navigate('/admin/campaigns')}>
          ← Back
        </Button>
        <h1 className="text-xl font-semibold">Campaign {id}</h1>
      </div>

      {/* Stepper */}
      <div className="flex items-center gap-0 mb-8 overflow-x-auto">
        {STEPS.map((label, i) => {
          const isCompleted = i < currentStep
          const isCurrent = i === currentStep
          const path = STEP_PATHS[i]
          const to = path ? `${base}/${path}` : null

          const circle = (
            <div
              className={cn(
                'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium shrink-0',
                isCompleted && 'bg-primary text-primary-foreground',
                isCurrent && 'border-2 border-primary text-primary',
                !isCompleted && !isCurrent && 'border-2 border-muted text-muted-foreground'
              )}
            >
              {isCompleted ? '✓' : i + 1}
            </div>
          )

          return (
            <div key={label} className="flex items-center">
              <div className="flex flex-col items-center gap-1">
                {isCompleted && to ? (
                  <Link to={to}>{circle}</Link>
                ) : (
                  circle
                )}
                <span
                  className={cn(
                    'text-xs whitespace-nowrap',
                    isCurrent && 'text-primary font-medium',
                    !isCompleted && !isCurrent && 'text-muted-foreground'
                  )}
                >
                  {label}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div
                  className={cn(
                    'h-0.5 w-12 mx-1 mb-4',
                    i < currentStep ? 'bg-primary' : 'bg-muted'
                  )}
                />
              )}
            </div>
          )
        })}
      </div>

      {campaign.status === 'pending' ? (
        <p className="text-muted-foreground text-sm">Generating concepts…</p>
      ) : (
        <Outlet />
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Admin/Campaigns/CampaignDetailPage.tsx
git commit -m "[TASK-020] feat: add CampaignDetailPage with stepper and status redirect"
```

---

### Task 8: ConceptsPage

**Files:**
- Create: `frontend/src/pages/Admin/Campaigns/ConceptsPage.tsx`

- [ ] **Step 1: Create ConceptsPage.tsx**

```typescript
import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useCampaign, useConfirmConcept } from '@/hooks/useCampaigns'
import { cn } from '@/lib/utils'

export function ConceptsPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: campaign, isLoading } = useCampaign(id!)
  const confirmConcept = useConfirmConcept(id!)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  if (isLoading) return <p className="text-muted-foreground text-sm">Loading…</p>
  if (!campaign) return null

  const handleConfirm = async () => {
    if (!selectedId) return
    await confirmConcept.mutateAsync(selectedId)
    navigate(`/admin/campaigns/${id}/plan`)
  }

  return (
    <div>
      <h2 className="text-lg font-semibold mb-4">Select a Concept</h2>
      <div className="grid gap-4 md:grid-cols-3 mb-6">
        {campaign.concepts.map((concept) => {
          const isSelected = selectedId === concept.id
          const isExpanded = expandedId === concept.id
          return (
            <Card
              key={concept.id}
              className={cn(
                'cursor-pointer transition-colors',
                isSelected && 'border-primary ring-2 ring-primary'
              )}
              onClick={() => setSelectedId(concept.id)}
            >
              <CardHeader className="pb-2">
                <CardTitle className="text-base">{concept.name}</CardTitle>
                <p className="text-sm text-muted-foreground italic">{concept.tagline}</p>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex flex-wrap gap-1">
                  {concept.channels.map((ch) => (
                    <Badge key={ch} variant="secondary" className="text-xs">{ch}</Badge>
                  ))}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="px-0 text-xs text-muted-foreground"
                  onClick={(e) => {
                    e.stopPropagation()
                    setExpandedId(isExpanded ? null : concept.id)
                  }}
                >
                  {isExpanded ? 'Show less ▲' : 'Show more ▼'}
                </Button>
                {isExpanded && (
                  <div className="space-y-2 text-sm">
                    <div>
                      <span className="font-medium">Tone:</span> {concept.tone_board}
                    </div>
                    <div>
                      <span className="font-medium">Audience:</span> {concept.target_audience}
                    </div>
                    <div className="space-y-1">
                      <span className="font-medium">Risk Flags:</span>
                      {concept.risk_flags.legal && (
                        <p className="text-amber-600 text-xs">Legal: {concept.risk_flags.legal}</p>
                      )}
                      {concept.risk_flags.regulatory && (
                        <p className="text-amber-600 text-xs">Regulatory: {concept.risk_flags.regulatory}</p>
                      )}
                      {concept.risk_flags.sensitivity && (
                        <p className="text-amber-600 text-xs">Sensitivity: {concept.risk_flags.sensitivity}</p>
                      )}
                      {!concept.risk_flags.legal && !concept.risk_flags.regulatory && !concept.risk_flags.sensitivity && (
                        <p className="text-green-600 text-xs">None</p>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )
        })}
      </div>

      {confirmConcept.isError && (
        <p className="text-destructive text-sm mb-2">Failed to confirm selection. Please try again.</p>
      )}

      <Button
        onClick={handleConfirm}
        disabled={!selectedId || confirmConcept.isPending}
      >
        {confirmConcept.isPending ? 'Confirming…' : 'Confirm Selection'}
      </Button>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Admin/Campaigns/ConceptsPage.tsx
git commit -m "[TASK-020] feat: add ConceptsPage with expandable concept cards"
```

---

### Task 9: PlanPage

**Files:**
- Create: `frontend/src/pages/Admin/Campaigns/PlanPage.tsx`

- [ ] **Step 1: Create PlanPage.tsx**

Note: Uses `useReactTable` directly (not `<DataTable>`) to support expandable rows with `getExpandedRowModel`.

```typescript
import { useState, Fragment } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  type ColumnDef,
  type ExpandedState,
  flexRender,
  getCoreRowModel,
  getExpandedRowModel,
  useReactTable,
} from '@tanstack/react-table'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { useCampaign, useActivationPlan, useApproveBudget } from '@/hooks/useCampaigns'
import type { Activation } from '@/types/admin'

export function PlanPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: campaign } = useCampaign(id!)
  const { data: planResult, isLoading: planLoading } = useActivationPlan(
    id!,
    campaign?.status === 'confirmed'
  )
  const approveBudget = useApproveBudget(id!)
  const [expanded, setExpanded] = useState<ExpandedState>({})

  const isGenerating = campaign?.status === 'confirmed' && planLoading
  const activations = (planResult ?? campaign)?.activation_plan ?? []

  const handleApprove = async () => {
    await approveBudget.mutateAsync()
    navigate(`/admin/campaigns/${id}/budget`)
  }

  const columns: ColumnDef<Activation>[] = [
    {
      id: 'expander',
      header: '',
      cell: ({ row }) => (
        <button
          onClick={() => row.toggleExpanded()}
          className="p-1 rounded text-muted-foreground hover:text-foreground"
        >
          {row.getIsExpanded() ? '▲' : '▼'}
        </button>
      ),
    },
    { accessorKey: 'channel', header: 'Channel' },
    { accessorKey: 'sub_channel', header: 'Sub-channel' },
    {
      accessorKey: 'budget',
      header: 'Budget',
      cell: ({ row }) =>
        `${row.original.currency} ${row.original.budget.toLocaleString()}`,
    },
    {
      id: 'kpis',
      header: 'KPIs',
      cell: ({ row }) => row.original.kpis.map((k) => k.name).join(', '),
    },
  ]

  const table = useReactTable({
    data: activations,
    columns,
    state: { expanded },
    onExpandedChange: setExpanded,
    getCoreRowModel: getCoreRowModel(),
    getExpandedRowModel: getExpandedRowModel(),
  })

  if (isGenerating) {
    return <p className="text-muted-foreground text-sm">Generating activation plan…</p>
  }

  return (
    <div>
      <h2 className="text-lg font-semibold mb-4">Activation Plan</h2>

      <div className="rounded-md border mb-6">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((hg) => (
              <TableRow key={hg.id}>
                {hg.headers.map((header) => (
                  <TableHead key={header.id}>
                    {flexRender(header.column.columnDef.header, header.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.length ? (
              table.getRowModel().rows.map((row) => (
                <Fragment key={row.id}>
                  <TableRow>
                    {row.getVisibleCells().map((cell) => (
                      <TableCell key={cell.id}>
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </TableCell>
                    ))}
                  </TableRow>
                  {row.getIsExpanded() && (
                    <TableRow>
                      <TableCell colSpan={columns.length} className="p-0">
                        <div className="bg-muted/30 p-4 space-y-3">
                          <div className="grid grid-cols-2 gap-2 text-sm">
                            <div><span className="font-medium">Channel:</span> {row.original.channel}</div>
                            <div><span className="font-medium">Sub-channel:</span> {row.original.sub_channel}</div>
                            <div>
                              <span className="font-medium">Budget:</span>{' '}
                              {row.original.currency} {row.original.budget.toLocaleString()}
                            </div>
                            <div><span className="font-medium">Audience:</span> {row.original.audience}</div>
                          </div>
                          <div>
                            <p className="font-medium text-sm mb-2">KPIs</p>
                            <table className="text-sm w-full">
                              <thead>
                                <tr className="text-left text-muted-foreground">
                                  <th className="pb-1">Name</th>
                                  <th className="pb-1">Target</th>
                                  <th className="pb-1">Unit</th>
                                </tr>
                              </thead>
                              <tbody>
                                {row.original.kpis.map((kpi) => (
                                  <tr key={kpi.name}>
                                    <td>{kpi.name}</td>
                                    <td>{kpi.target}</td>
                                    <td>{kpi.unit}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </Fragment>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="text-center text-muted-foreground py-8">
                  No activations.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {approveBudget.isError && (
        <p className="text-destructive text-sm mb-2">Failed to approve budget. Please try again.</p>
      )}

      <Button onClick={handleApprove} disabled={approveBudget.isPending || activations.length === 0}>
        {approveBudget.isPending ? 'Approving…' : 'Approve Budget'}
      </Button>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Admin/Campaigns/PlanPage.tsx
git commit -m "[TASK-020] feat: add PlanPage with expandable activation table"
```

---

### Task 10: BudgetPage

**Files:**
- Create: `frontend/src/pages/Admin/Campaigns/BudgetPage.tsx`

- [ ] **Step 1: Create BudgetPage.tsx**

```typescript
import { useParams } from 'react-router-dom'
import type { ColumnDef } from '@tanstack/react-table'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { DataTable } from '@/components/data-table'
import { Button } from '@/components/ui/button'
import { useCampaign, useConfirmBudget } from '@/hooks/useCampaigns'
import type { BudgetAllocation } from '@/types/admin'

export function BudgetPage() {
  const { id } = useParams<{ id: string }>()
  const { data: campaign, isLoading } = useCampaign(id!)
  const confirmBudget = useConfirmBudget(id!)

  if (isLoading) return <p className="text-muted-foreground text-sm">Loading…</p>
  if (!campaign) return null

  const { budget_proposal, status } = campaign

  if (!budget_proposal) {
    return <p className="text-muted-foreground text-sm">No budget proposal available.</p>
  }

  const allocationColumns: ColumnDef<BudgetAllocation>[] = [
    { accessorKey: 'channel', header: 'Channel' },
    {
      accessorKey: 'amount',
      header: 'Amount',
      cell: ({ row }) =>
        `${budget_proposal.currency} ${row.original.amount.toLocaleString()}`,
    },
    {
      accessorKey: 'percentage',
      header: 'Share',
      cell: ({ row }) => `${row.original.percentage}%`,
    },
  ]

  return (
    <div className="space-y-6">
      {status === 'approved' && (
        <div className="rounded-md bg-green-50 border border-green-200 px-4 py-3 text-green-800 font-medium">
          Campaign Approved ✓
        </div>
      )}

      <Card className="w-fit">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Budget Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-2xl font-bold">
            {budget_proposal.currency}{' '}
            {budget_proposal.total_budget.toLocaleString()}
          </p>
        </CardContent>
      </Card>

      <div>
        <h3 className="text-sm font-medium mb-3">Allocations</h3>
        <DataTable columns={allocationColumns} data={budget_proposal.allocations} />
      </div>

      {confirmBudget.isError && (
        <p className="text-destructive text-sm">Failed to confirm budget. Please try again.</p>
      )}

      {status !== 'approved' && (
        <Button onClick={() => confirmBudget.mutate()} disabled={confirmBudget.isPending}>
          {confirmBudget.isPending ? 'Confirming…' : 'Confirm Budget'}
        </Button>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Admin/Campaigns/BudgetPage.tsx
git commit -m "[TASK-020] feat: add BudgetPage with budget summary and confirm"
```

---

### Task 11: Routing + Sidebar + Build Verify

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Sidebar.tsx`

- [ ] **Step 1: Update App.tsx**

Replace the full content of `frontend/src/App.tsx` with:

```typescript
import { createBrowserRouter, Navigate } from 'react-router-dom'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { AdminLayout } from '@/components/AdminLayout'
import { LoginPage } from '@/pages/Login/LoginPage'
import { TenantsPage } from '@/pages/Admin/Tenants/TenantsPage'
import { UsersPage } from '@/pages/Admin/Users/UsersPage'
import { RolesPage } from '@/pages/Admin/Roles/RolesPage'
import { AuditLogPage } from '@/pages/Admin/AuditLog/AuditLogPage'
import { HealthPage } from '@/pages/Admin/Health/HealthPage'
import { AnalyticsPage } from '@/pages/Admin/Analytics/AnalyticsPage'
import { CampaignsPage } from '@/pages/Admin/Campaigns/CampaignsPage'
import { CampaignDetailPage } from '@/pages/Admin/Campaigns/CampaignDetailPage'
import { ConceptsPage } from '@/pages/Admin/Campaigns/ConceptsPage'
import { PlanPage } from '@/pages/Admin/Campaigns/PlanPage'
import { BudgetPage } from '@/pages/Admin/Campaigns/BudgetPage'

export const router = createBrowserRouter([
  { path: '/', element: <Navigate to="/admin/tenants" replace /> },
  { path: '/login', element: <LoginPage /> },
  {
    path: '/admin',
    element: <ProtectedRoute />,
    children: [
      {
        element: <AdminLayout />,
        children: [
          { index: true, element: <Navigate to="/admin/tenants" replace /> },
          { path: 'tenants', element: <TenantsPage /> },
          { path: 'users', element: <UsersPage /> },
          { path: 'roles', element: <RolesPage /> },
          { path: 'audit', element: <AuditLogPage /> },
          { path: 'health', element: <HealthPage /> },
          { path: 'analytics', element: <AnalyticsPage /> },
          { path: 'campaigns', element: <CampaignsPage /> },
          {
            path: 'campaigns/:id',
            element: <CampaignDetailPage />,
            children: [
              { path: 'concepts', element: <ConceptsPage /> },
              { path: 'plan', element: <PlanPage /> },
              { path: 'budget', element: <BudgetPage /> },
            ],
          },
        ],
      },
    ],
  },
  {
    path: '/403',
    element: (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-semibold">Access Denied</h1>
          <p className="text-muted-foreground mt-2">
            You don't have permission to view this page.
          </p>
        </div>
      </div>
    ),
  },
])
```

- [ ] **Step 2: Update Sidebar.tsx**

Replace the `navItems` array in `frontend/src/components/Sidebar.tsx`:

Change the import line from:
```typescript
import { Building2, Users, Shield, ClipboardList, Activity, BarChart2, LogOut } from 'lucide-react'
```
to:
```typescript
import { Building2, Users, Shield, ClipboardList, Activity, BarChart2, Megaphone, LogOut } from 'lucide-react'
```

Replace the `navItems` array with:
```typescript
const navItems = [
  { label: 'Tenants',   to: '/admin/tenants',   icon: Building2 },
  { label: 'Users',     to: '/admin/users',      icon: Users },
  { label: 'Roles',     to: '/admin/roles',      icon: Shield },
  { label: 'Audit Log', to: '/admin/audit',      icon: ClipboardList },
  { label: 'Health',    to: '/admin/health',     icon: Activity },
  { label: 'Analytics', to: '/admin/analytics',  icon: BarChart2 },
  { label: 'Campaigns', to: '/admin/campaigns',  icon: Megaphone },
]
```

- [ ] **Step 3: Run build**

```
cd frontend && npm run build
```
Expected: Build succeeds with no TypeScript errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/Sidebar.tsx
git commit -m "[TASK-020] feat: add campaign routes and Campaigns sidebar nav item"
```
