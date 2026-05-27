import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
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
  const isAdmin = !!user
  const navigate = useNavigate()

  const { data: tenants = [] } = useTenants()
  const [selectedTenantId, setSelectedTenantId] = useState<string | null>(null)
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
  const activations = summaries.flatMap((s) => s.activations)
  const activeActivations = activations.filter((a) => a.status !== 'no_kpis').length
  const totalSpend = activations.reduce((sum, a) => sum + (a.metrics.spend ?? 0), 0)
  const allAchievements = activations.flatMap((a) => a.kpi_results.map((k) => k.achievement_percent))
  const avgAchievement =
    allAchievements.length
      ? Math.round(allAchievements.reduce((s, v) => s + v, 0) / allAchievements.length)
      : 0

  const allAlerts = summaries.flatMap((s) => s.red_alerts)
  const visibleAlerts = allAlerts.filter((a) => !dismissedAlerts.has(a.activation_id))
  const channelTotals = aggregateChannels(summaries)

  const alertColumns: ColumnDef<RedAlert>[] = useMemo(() => [
    {
      id: 'mandate',
      header: 'Mandate',
      cell: ({ row }: { row: any }) => {
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
      cell: ({ row }: { row: any }) => {
        const alert = row.original
        const state = replanStates[alert.activation_id] ?? 'idle'
        return (
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="destructive"
              disabled={state === 'queued'}
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
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate(`/admin/campaigns/${alert.campaign_id}/kpis`)}
            >
              View KPIs
            </Button>
          </div>
        )
      },
    },
  ], [replanStates, summaries, navigate])

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
                {tenants.map((t: any) => (
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
