# Frontend Analytics Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an `/admin/analytics` page to the NTM admin SPA with role-aware tenant selector, RAG summary cards, channel breakdown, trend charts, and a red-alerts table with replan/dismiss actions (all data via MSW mocks).

**Architecture:** Single `AnalyticsPage` inside the existing `AdminLayout`. `platform_admin` sees a tenant selector; `campaign_manager` is locked to their own tenant. Four new MSW endpoints power two React Query hooks. No new libraries — Recharts, shadcn/ui, and TanStack Table are already installed.

**Tech Stack:** React 18, TypeScript, Vite, Recharts, TanStack Query v5, TanStack Table v8, shadcn/ui, MSW v2, Zustand, react-router-dom v7

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `frontend/src/types/admin.ts` | Add analytics types; add `tenant_id?` to AuthUser |
| Modify | `frontend/src/store/useAuthStore.ts` | Add `tenant_id?` to `AuthUser` interface |
| Create | `frontend/src/mocks/db/analytics.ts` | Seed data: 3 mandates × 3 channels, 30-day trends |
| Create | `frontend/src/mocks/handlers/analytics.ts` | 4 MSW handlers |
| Modify | `frontend/src/mocks/browser.ts` | Register analytics handlers |
| Modify | `frontend/src/mocks/handlers/auth.ts` | Return `tenant_id` for non-admin users |
| Modify | `frontend/src/api/admin.ts` | 4 new API functions |
| Create | `frontend/src/hooks/useAnalytics.ts` | React Query hooks |
| Create | `frontend/src/pages/Admin/Analytics/AnalyticsPage.tsx` | Full analytics page |
| Modify | `frontend/src/App.tsx` | Add `/admin/analytics` route |
| Modify | `frontend/src/components/Sidebar.tsx` | Add Analytics nav item |

---

## Task 1: Analytics Types

**Files:**
- Modify: `frontend/src/types/admin.ts`
- Modify: `frontend/src/store/useAuthStore.ts`

- [ ] **Step 1: Add analytics interfaces to `types/admin.ts`**

Append to the end of the file:

```typescript
export interface KpiResult {
  kpi_name: string
  target: number
  actual: number
  achievement_percent: number
  threshold_unit: string
  status: 'red' | 'amber' | 'green' | 'no_kpis'
}

export interface AnalyticsActivation {
  activation_id: string
  campaign_id: string
  channel: string
  sub_channel?: string
  status: 'red' | 'amber' | 'green' | 'no_kpis'
  kpi_results: KpiResult[]
  metrics: {
    impressions: number
    clicks: number
    conversions: number
    spend: number
  }
}

export interface RedAlert {
  activation_id: string
  campaign_id: string
  channel: string
  failed_kpi: string
  severity: 'red'
}

export interface ChannelSummaryItem {
  total: number
  red: number
  amber: number
  green: number
}

export interface AnalyticsSummary {
  mandate_id: string
  date: string
  summary_generated_at: string
  activations: AnalyticsActivation[]
  red_alerts: RedAlert[]
  summary_by_channel: Record<string, ChannelSummaryItem>
}

export interface TrendPoint {
  date: string
  spend: number
  impressions: number
}
```

- [ ] **Step 2: Add `tenant_id?` to `AuthUser` in `useAuthStore.ts`**

Replace the `AuthUser` interface:

```typescript
interface AuthUser {
  id: string
  email: string
  role: string
  tenant_id?: string
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/admin.ts frontend/src/store/useAuthStore.ts
git commit -m "[fe-analytics] feat: add analytics types and tenant_id to AuthUser"
```

---

## Task 2: MSW Seed Data + Handlers

**Files:**
- Create: `frontend/src/mocks/db/analytics.ts`
- Create: `frontend/src/mocks/handlers/analytics.ts`
- Modify: `frontend/src/mocks/browser.ts`
- Modify: `frontend/src/mocks/handlers/auth.ts`

- [ ] **Step 1: Create `frontend/src/mocks/db/analytics.ts`**

```typescript
import type { AnalyticsSummary, TrendPoint } from '@/types/admin'

const TODAY = new Date().toISOString().split('T')[0]

export const analyticsSummaries: AnalyticsSummary[] = [
  {
    mandate_id: 'm-001',
    date: TODAY,
    summary_generated_at: new Date().toISOString(),
    activations: [
      {
        activation_id: 'act-001-ga',
        campaign_id: 'camp-001',
        channel: 'google_ads',
        sub_channel: 'Google Search',
        status: 'green',
        kpi_results: [{ kpi_name: 'conversion_rate', target: 3.0, actual: 3.5, achievement_percent: 16.7, threshold_unit: 'percent', status: 'green' }],
        metrics: { impressions: 12000, clicks: 600, conversions: 21, spend: 900 },
      },
      {
        activation_id: 'act-001-ma',
        campaign_id: 'camp-001',
        channel: 'meta_ads',
        status: 'amber',
        kpi_results: [{ kpi_name: 'roas', target: 3.0, actual: 2.7, achievement_percent: -10.0, threshold_unit: 'ratio', status: 'amber' }],
        metrics: { impressions: 8000, clicks: 400, conversions: 12, spend: 600 },
      },
      {
        activation_id: 'act-001-li',
        campaign_id: 'camp-001',
        channel: 'linkedin_ads',
        status: 'green',
        kpi_results: [{ kpi_name: 'ctr', target: 0.03, actual: 0.04, achievement_percent: 33.3, threshold_unit: 'percent', status: 'green' }],
        metrics: { impressions: 5000, clicks: 200, conversions: 5, spend: 400 },
      },
    ],
    red_alerts: [],
    summary_by_channel: {
      google_ads: { total: 1, red: 0, amber: 0, green: 1 },
      meta_ads: { total: 1, red: 0, amber: 1, green: 0 },
      linkedin_ads: { total: 1, red: 0, amber: 0, green: 1 },
    },
  },
  {
    mandate_id: 'm-002',
    date: TODAY,
    summary_generated_at: new Date().toISOString(),
    activations: [
      {
        activation_id: 'act-002-ga',
        campaign_id: 'camp-002',
        channel: 'google_ads',
        sub_channel: 'Google Display',
        status: 'red',
        kpi_results: [{ kpi_name: 'conversion_rate', target: 3.0, actual: 2.0, achievement_percent: -33.3, threshold_unit: 'percent', status: 'red' }],
        metrics: { impressions: 15000, clicks: 300, conversions: 6, spend: 1200 },
      },
      {
        activation_id: 'act-002-ma',
        campaign_id: 'camp-002',
        channel: 'meta_ads',
        status: 'green',
        kpi_results: [{ kpi_name: 'roas', target: 2.0, actual: 2.5, achievement_percent: 25.0, threshold_unit: 'ratio', status: 'green' }],
        metrics: { impressions: 9000, clicks: 450, conversions: 18, spend: 700 },
      },
      {
        activation_id: 'act-002-li',
        campaign_id: 'camp-002',
        channel: 'linkedin_ads',
        status: 'amber',
        kpi_results: [{ kpi_name: 'ctr', target: 0.05, actual: 0.045, achievement_percent: -10.0, threshold_unit: 'percent', status: 'amber' }],
        metrics: { impressions: 4000, clicks: 180, conversions: 4, spend: 350 },
      },
    ],
    red_alerts: [
      { activation_id: 'act-002-ga', campaign_id: 'camp-002', channel: 'google_ads', failed_kpi: 'conversion_rate', severity: 'red' },
    ],
    summary_by_channel: {
      google_ads: { total: 1, red: 1, amber: 0, green: 0 },
      meta_ads: { total: 1, red: 0, amber: 0, green: 1 },
      linkedin_ads: { total: 1, red: 0, amber: 1, green: 0 },
    },
  },
  {
    mandate_id: 'm-003',
    date: TODAY,
    summary_generated_at: new Date().toISOString(),
    activations: [
      {
        activation_id: 'act-003-ga',
        campaign_id: 'camp-003',
        channel: 'google_ads',
        status: 'amber',
        kpi_results: [{ kpi_name: 'cpc', target: 1.50, actual: 1.65, achievement_percent: -10.0, threshold_unit: 'currency', status: 'amber' }],
        metrics: { impressions: 10000, clicks: 500, conversions: 15, spend: 825 },
      },
      {
        activation_id: 'act-003-ma',
        campaign_id: 'camp-003',
        channel: 'meta_ads',
        status: 'red',
        kpi_results: [{ kpi_name: 'roas', target: 3.0, actual: 1.5, achievement_percent: -50.0, threshold_unit: 'ratio', status: 'red' }],
        metrics: { impressions: 6000, clicks: 300, conversions: 5, spend: 800 },
      },
      {
        activation_id: 'act-003-li',
        campaign_id: 'camp-003',
        channel: 'linkedin_ads',
        status: 'green',
        kpi_results: [{ kpi_name: 'engagement_rate', target: 0.05, actual: 0.06, achievement_percent: 20.0, threshold_unit: 'percent', status: 'green' }],
        metrics: { impressions: 3500, clicks: 210, conversions: 8, spend: 280 },
      },
    ],
    red_alerts: [
      { activation_id: 'act-003-ma', campaign_id: 'camp-003', channel: 'meta_ads', failed_kpi: 'roas', severity: 'red' },
    ],
    summary_by_channel: {
      google_ads: { total: 1, red: 0, amber: 1, green: 0 },
      meta_ads: { total: 1, red: 1, amber: 0, green: 0 },
      linkedin_ads: { total: 1, red: 0, amber: 0, green: 1 },
    },
  },
]

// 30 days of trend data
function generateTrends(): TrendPoint[] {
  const points: TrendPoint[] = []
  const base = new Date()
  base.setDate(base.getDate() - 29)
  for (let i = 0; i < 30; i++) {
    const d = new Date(base)
    d.setDate(base.getDate() + i)
    points.push({
      date: d.toISOString().split('T')[0],
      spend: Math.round(500 + Math.random() * 300 + i * 10),
      impressions: Math.round(8000 + Math.random() * 4000 + i * 100),
    })
  }
  return points
}

export const analyticsTrends: TrendPoint[] = generateTrends()
```

- [ ] **Step 2: Create `frontend/src/mocks/handlers/analytics.ts`**

```typescript
import { http, HttpResponse } from 'msw'
import { analyticsSummaries, analyticsTrends } from '../db/analytics'

export const analyticsHandlers = [
  http.get('/api/v1/analytics/summary', () => {
    return HttpResponse.json(analyticsSummaries)
  }),

  http.get('/api/v1/analytics/trends', ({ request }) => {
    const url = new URL(request.url)
    const days = parseInt(url.searchParams.get('days') ?? '7')
    return HttpResponse.json(analyticsTrends.slice(-days))
  }),

  http.post('/api/v1/campaigns/:id/replan', ({ params }) => {
    return HttpResponse.json({ status: 'queued', job_id: `job-${params.id}-${Date.now()}` })
  }),

  http.delete('/api/v1/alerts/:id', () => {
    return new HttpResponse(null, { status: 204 })
  }),
]
```

- [ ] **Step 3: Register analytics handlers in `browser.ts`**

Replace the existing `browser.ts` content:

```typescript
import { setupWorker } from 'msw/browser'
import { authHandlers } from './handlers/auth'
import { tenantHandlers } from './handlers/tenants'
import { userHandlers } from './handlers/users'
import { roleHandlers } from './handlers/roles'
import { auditHandlers } from './handlers/audit'
import { healthHandlers } from './handlers/health'
import { analyticsHandlers } from './handlers/analytics'

export const worker = setupWorker(
  ...authHandlers,
  ...tenantHandlers,
  ...userHandlers,
  ...roleHandlers,
  ...auditHandlers,
  ...healthHandlers,
  ...analyticsHandlers,
)
```

- [ ] **Step 4: Update `auth.ts` handler to include `tenant_id` for campaign_manager**

Replace the existing `authHandlers` in `frontend/src/mocks/handlers/auth.ts`:

```typescript
import { http, HttpResponse } from 'msw'

export const authHandlers = [
  http.post('/api/v1/auth/login', async ({ request }) => {
    const body = await request.json() as { email: string; password: string }
    const isCampaignManager = body.email.includes('manager')
    return HttpResponse.json({
      token: 'mock-jwt-token',
      user: {
        id: isCampaignManager ? 'cm-1' : 'admin-1',
        email: body.email,
        role: isCampaignManager ? 'campaign_manager' : 'platform_admin',
        tenant_id: isCampaignManager ? 't1' : undefined,
      },
    })
  }),
]
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/mocks/
git commit -m "[fe-analytics] feat: add analytics MSW seed data and handlers"
```

---

## Task 3: API Client Functions

**Files:**
- Modify: `frontend/src/api/admin.ts`

- [ ] **Step 1: Append 4 analytics functions to `admin.ts`**

Add at the end of `frontend/src/api/admin.ts`:

```typescript
export const getAnalyticsSummary = (tenantId: string, date: string) =>
  apiClient
    .get(`/analytics/summary?tenant_id=${tenantId}&date=${date}`)
    .then((r) => r.data)

export const getAnalyticsTrends = (
  tenantId: string,
  mandateId: string | null,
  days: 7 | 30
) => {
  const params = new URLSearchParams({ tenant_id: tenantId, days: String(days) })
  if (mandateId) params.set('mandate_id', mandateId)
  return apiClient.get(`/analytics/trends?${params}`).then((r) => r.data)
}

export const triggerReplan = (campaignId: string) =>
  apiClient.post(`/campaigns/${campaignId}/replan`).then((r) => r.data)

export const dismissAlert = (alertId: string) =>
  apiClient.delete(`/alerts/${alertId}`).then((r) => r.data)
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/admin.ts
git commit -m "[fe-analytics] feat: add analytics API client functions"
```

---

## Task 4: React Query Hooks

**Files:**
- Create: `frontend/src/hooks/useAnalytics.ts`

- [ ] **Step 1: Create `frontend/src/hooks/useAnalytics.ts`**

```typescript
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  getAnalyticsSummary,
  getAnalyticsTrends,
  triggerReplan,
  dismissAlert,
} from '@/api/admin'
import type { AnalyticsSummary, TrendPoint } from '@/types/admin'

export function useAnalyticsSummary(tenantId: string | null, date: string) {
  return useQuery<AnalyticsSummary[]>({
    queryKey: ['analytics-summary', tenantId, date],
    queryFn: () => getAnalyticsSummary(tenantId!, date),
    enabled: !!tenantId,
    staleTime: 5 * 60 * 1000,
  })
}

export function useAnalyticsTrends(
  tenantId: string | null,
  mandateId: string | null,
  days: 7 | 30
) {
  return useQuery<TrendPoint[]>({
    queryKey: ['analytics-trends', tenantId, mandateId, days],
    queryFn: () => getAnalyticsTrends(tenantId!, mandateId, days),
    enabled: !!tenantId,
  })
}

export function useTriggerReplan() {
  return useMutation({
    mutationFn: (campaignId: string) => triggerReplan(campaignId),
  })
}

export function useDismissAlert() {
  return useMutation({
    mutationFn: (alertId: string) => dismissAlert(alertId),
  })
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/hooks/useAnalytics.ts
git commit -m "[fe-analytics] feat: add useAnalytics React Query hooks"
```

---

## Task 5: AnalyticsPage Component

**Files:**
- Create: `frontend/src/pages/Admin/Analytics/AnalyticsPage.tsx`

- [ ] **Step 1: Create `frontend/src/pages/Admin/Analytics/AnalyticsPage.tsx`**

```typescript
import { useState } from 'react'
import type { ColumnDef } from '@tanstack/react-table'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { PageHeader } from '@/components/PageHeader'
import { DataTable } from '@/components/data-table'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useAuthStore } from '@/store/useAuthStore'
import { useTenants } from '@/hooks/useTenants'
import {
  useAnalyticsSummary,
  useAnalyticsTrends,
  useTriggerReplan,
  useDismissAlert,
} from '@/hooks/useAnalytics'
import type { RedAlert, AnalyticsSummary } from '@/types/admin'

const TODAY = new Date().toISOString().split('T')[0]

type ReplanState = 'idle' | 'queued' | 'error'

function ragBadge(status: string) {
  if (status === 'red') return <Badge variant="destructive">RED</Badge>
  if (status === 'amber') return <Badge variant="outline" className="border-amber-400 text-amber-600">AMBER</Badge>
  if (status === 'green') return <Badge variant="default">GREEN</Badge>
  return <Badge variant="secondary">NO KPIS</Badge>
}

function aggregateChannels(summaries: AnalyticsSummary[]) {
  const totals: Record<string, { total: number; red: number; amber: number; green: number }> = {}
  for (const s of summaries) {
    for (const [ch, counts] of Object.entries(s.summary_by_channel)) {
      if (!totals[ch]) totals[ch] = { total: 0, red: 0, amber: 0, green: 0 }
      totals[ch].total += counts.total
      totals[ch].red += counts.red
      totals[ch].amber += counts.amber
      totals[ch].green += counts.green
    }
  }
  return totals
}

export function AnalyticsPage() {
  const { user } = useAuthStore()
  const isAdmin = user?.role === 'platform_admin'

  const { data: tenants = [] } = useTenants()
  const [selectedTenantId, setSelectedTenantId] = useState<string | null>(
    isAdmin ? null : (user?.tenant_id ?? null)
  )
  const [dateRange, setDateRange] = useState<7 | 30>(7)
  const [dismissedAlerts, setDismissedAlerts] = useState<Set<string>>(new Set())
  const [replanStates, setReplanStates] = useState<Record<string, ReplanState>>({})

  const { data: summaries = [], isLoading: summaryLoading } = useAnalyticsSummary(
    selectedTenantId,
    TODAY
  )
  const { data: trends = [], isLoading: trendsLoading } = useAnalyticsTrends(
    selectedTenantId,
    null,
    dateRange
  )
  const triggerReplan = useTriggerReplan()
  const dismissAlert = useDismissAlert()

  const totalMandates = summaries.length
  const activeActivations = summaries.flatMap((s) =>
    s.activations.filter((a) => a.status !== 'no_kpis')
  ).length
  const totalSpend = summaries
    .flatMap((s) => s.activations)
    .reduce((sum, a) => sum + (a.metrics.spend ?? 0), 0)
  const allAchievements = summaries
    .flatMap((s) => s.activations)
    .flatMap((a) => a.kpi_results.map((k) => k.achievement_percent))
  const avgAchievement =
    allAchievements.length
      ? Math.round(allAchievements.reduce((s, v) => s + v, 0) / allAchievements.length)
      : 0

  const allAlerts = summaries.flatMap((s) => s.red_alerts)
  const visibleAlerts = allAlerts.filter((a) => !dismissedAlerts.has(a.activation_id))
  const channelTotals = aggregateChannels(summaries)

  const alertColumns: ColumnDef<RedAlert>[] = [
    {
      accessorKey: 'mandate_id',
      header: 'Mandate',
      cell: ({ row }) => {
        const s = summaries.find((s) =>
          s.red_alerts.some((a) => a.activation_id === row.original.activation_id)
        )
        return <span className="font-mono text-xs">{s?.mandate_id ?? '—'}</span>
      },
    },
    { accessorKey: 'channel', header: 'Channel' },
    { accessorKey: 'failed_kpi', header: 'Failed KPI' },
    {
      id: 'severity',
      header: 'Status',
      cell: () => ragBadge('red'),
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: ({ row }) => {
        const alert = row.original
        const state = replanStates[alert.activation_id] ?? 'idle'
        return (
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="destructive"
              disabled={state === 'queued' || triggerReplan.isPending}
              onClick={async () => {
                try {
                  await triggerReplan.mutateAsync(alert.campaign_id)
                  setReplanStates((prev) => ({ ...prev, [alert.activation_id]: 'queued' }))
                } catch {
                  setReplanStates((prev) => ({ ...prev, [alert.activation_id]: 'error' }))
                }
              }}
            >
              {state === 'queued' ? 'Queued ✓' : state === 'error' ? 'Failed' : 'Replan'}
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                dismissAlert.mutate(alert.activation_id)
                setDismissedAlerts((prev) => new Set(prev).add(alert.activation_id))
              }}
            >
              Dismiss
            </Button>
          </div>
        )
      },
    },
  ]

  return (
    <div>
      <PageHeader title="Analytics" description="Campaign performance and KPI tracking." />

      <div className="flex gap-4 mb-6 flex-wrap">
        {isAdmin && (
          <div className="w-56">
            <Select onValueChange={setSelectedTenantId}>
              <SelectTrigger>
                <SelectValue placeholder="Select tenant…" />
              </SelectTrigger>
              <SelectContent>
                {tenants.map((t) => (
                  <SelectItem key={t.id} value={t.id}>
                    {t.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
        <div className="flex gap-1">
          <Button
            size="sm"
            variant={dateRange === 7 ? 'default' : 'outline'}
            onClick={() => setDateRange(7)}
          >
            7d
          </Button>
          <Button
            size="sm"
            variant={dateRange === 30 ? 'default' : 'outline'}
            onClick={() => setDateRange(30)}
          >
            30d
          </Button>
        </div>
      </div>

      {!selectedTenantId ? (
        <p className="text-muted-foreground text-sm">Select a tenant to view analytics.</p>
      ) : summaryLoading ? (
        <p className="text-muted-foreground text-sm">Loading…</p>
      ) : summaries.length === 0 ? (
        <p className="text-muted-foreground text-sm">No analytics data for this tenant yet.</p>
      ) : (
        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              { label: 'Total Mandates', value: String(totalMandates) },
              { label: 'Active Activations', value: String(activeActivations) },
              {
                label: 'Total Spend',
                value: `$${totalSpend.toLocaleString('en-US', { maximumFractionDigits: 0 })}`,
              },
              { label: 'Avg KPI Achievement', value: `${avgAchievement}%` },
            ].map(({ label, value }) => (
              <Card key={label}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    {label}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-bold">{value}</p>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Channel Breakdown */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {Object.entries(channelTotals).map(([channel, counts]) => (
              <Card key={channel}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">
                    {channel.replace(/_/g, ' ').toUpperCase()}
                  </CardTitle>
                </CardHeader>
                <CardContent className="flex gap-2 flex-wrap">
                  <Badge variant="destructive">{counts.red} red</Badge>
                  <Badge variant="outline" className="border-amber-400 text-amber-600">
                    {counts.amber} amber
                  </Badge>
                  <Badge variant="default">{counts.green} green</Badge>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Trend Charts */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">Spend over time</CardTitle>
              </CardHeader>
              <CardContent>
                {trendsLoading ? (
                  <p className="text-muted-foreground text-sm">Loading…</p>
                ) : (
                  <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={trends}>
                      <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Line
                        type="monotone"
                        dataKey="spend"
                        stroke="hsl(var(--primary))"
                        strokeWidth={2}
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">Impressions over time</CardTitle>
              </CardHeader>
              <CardContent>
                {trendsLoading ? (
                  <p className="text-muted-foreground text-sm">Loading…</p>
                ) : (
                  <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={trends}>
                      <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Line
                        type="monotone"
                        dataKey="impressions"
                        stroke="hsl(var(--primary))"
                        strokeWidth={2}
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Red Alerts */}
          <div>
            <h3 className="text-sm font-semibold mb-3">
              Red Alerts{visibleAlerts.length > 0 && ` (${visibleAlerts.length})`}
            </h3>
            {visibleAlerts.length === 0 ? (
              <p className="text-muted-foreground text-sm">No active alerts.</p>
            ) : (
              <DataTable columns={alertColumns} data={visibleAlerts} />
            )}
          </div>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Admin/Analytics/
git commit -m "[fe-analytics] feat: add AnalyticsPage with summary cards, channel breakdown, trend charts, and alerts table"
```

---

## Task 6: Routing, Sidebar, and Build Verify

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Sidebar.tsx`

- [ ] **Step 1: Add route to `App.tsx`**

Add import after the HealthPage import:

```typescript
import { AnalyticsPage } from '@/pages/Admin/Analytics/AnalyticsPage'
```

Add route inside the `AdminLayout` children array after `{ path: 'health', element: <HealthPage /> }`:

```typescript
{ path: 'analytics', element: <AnalyticsPage /> },
```

- [ ] **Step 2: Add Analytics nav item to `Sidebar.tsx`**

Add `BarChart2` to the lucide-react import (already has `Building2, Users, Shield, ClipboardList, Activity, LogOut`):

```typescript
import { Building2, Users, Shield, ClipboardList, Activity, BarChart2, LogOut } from 'lucide-react'
```

Add to the `navItems` array after Health:

```typescript
{ label: 'Analytics', to: '/admin/analytics', icon: BarChart2 },
```

- [ ] **Step 3: Run build to verify TypeScript and imports**

Run from `frontend/` directory:
```bash
npm run build
```

Expected: Build succeeds with no TypeScript errors. If there are errors, fix them before committing.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/Sidebar.tsx
git commit -m "[fe-analytics] feat: wire analytics route and sidebar nav item"
```

---

## Self-Review Checklist

- [x] **Spec coverage:** Types ✓, MSW endpoints ✓ (summary, trends, replan, dismiss), role gate ✓, summary cards ✓, channel breakdown ✓, trend charts ✓, red alerts table ✓, actions ✓, routing ✓, sidebar ✓
- [x] **Placeholders:** None — all code is complete
- [x] **Type consistency:** `RedAlert` includes `campaign_id` (used in replan call). `AnalyticsSummary[]` returned by hook. `TrendPoint` used by trends hook. All match across tasks.
- [x] **Import paths:** `@/components/data-table` (lowercase) matches UsersPage import. `@/store/useAuthStore` matches existing pattern.
