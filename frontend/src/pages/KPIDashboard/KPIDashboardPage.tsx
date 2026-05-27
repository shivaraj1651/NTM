import { useState, useMemo } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { AlertCircle, TrendingUp } from 'lucide-react'
import { useTenants } from '@/hooks/useTenants'
import { useMandateList } from '@/hooks/useMandates'
import { useAnalyticsSummary, useAnalyticsTrends, useTriggerReplan } from '@/hooks/useAnalytics'
import { useAuthStore } from '@/store/useAuthStore'
import { PageHeader } from '@/components/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { KpiResult } from '@/types/admin'

const RAG: Record<string, string> = {
  green: 'bg-green-100 text-green-800 border-green-300',
  amber: 'bg-amber-100 text-amber-800 border-amber-300',
  red: 'bg-red-100 text-red-800 border-red-300',
  no_kpis: 'bg-muted text-muted-foreground border-muted',
}

function KpiGauge({ kpi }: { kpi: KpiResult }) {
  const pct = Math.min(kpi.achievement_percent, 100)
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium">{kpi.kpi_name}</span>
        <Badge
          variant="outline"
          className={RAG[kpi.status] ?? RAG.no_kpis}
        >
          {kpi.achievement_percent}%
        </Badge>
      </div>
      <div className="w-full h-2 rounded-full bg-muted overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${
            kpi.status === 'green'
              ? 'bg-green-500'
              : kpi.status === 'amber'
              ? 'bg-amber-400'
              : 'bg-red-500'
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>Actual: {kpi.actual}</span>
        <span>Target: {kpi.target} {kpi.threshold_unit}</span>
      </div>
    </div>
  )
}

export function KPIDashboardPage() {
  const { user } = useAuthStore()
  const isAdmin = !!user

  const { data: tenants = [] } = useTenants()
  const [tenantId, setTenantId] = useState<string | null>(null)
  const [mandateId, setMandateId] = useState<string | null>(null)
  const [days, setDays] = useState<7 | 30>(7)

  const today = new Date().toISOString().slice(0, 10)
  const { data: summaries = [], isLoading: sumLoading } = useAnalyticsSummary(tenantId, today)
  const { data: trends = [] } = useAnalyticsTrends(tenantId, mandateId, days)
  const { data: mandates = [] } = useMandateList(tenantId)
  const triggerReplan = useTriggerReplan()

  const filtered = useMemo(
    () => (mandateId ? summaries.filter((s) => s.mandate_id === mandateId) : summaries),
    [summaries, mandateId],
  )

  const allKpis = useMemo(
    () => filtered.flatMap((s) => s.activations.flatMap((a) => a.kpi_results)),
    [filtered],
  )

  const redAlerts = useMemo(
    () => filtered.flatMap((s) => s.red_alerts),
    [filtered],
  )

  const totals = useMemo(() => {
    const green = allKpis.filter((k) => k.status === 'green').length
    const amber = allKpis.filter((k) => k.status === 'amber').length
    const red = allKpis.filter((k) => k.status === 'red').length
    return { green, amber, red, total: allKpis.length }
  }, [allKpis])

  return (
    <div className="space-y-6">
      <PageHeader title="KPI / KRA Dashboard" description="Campaign performance against targets." />

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        {isAdmin && (
          <Select onValueChange={(v) => { setTenantId(v); setMandateId(null) }}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="Select tenant…" />
            </SelectTrigger>
            <SelectContent>
              {(tenants as any[]).map((t) => (
                <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
        {tenantId && (
          <Select onValueChange={(v) => setMandateId(v === '__all__' ? null : v)}>
            <SelectTrigger className="w-56">
              <SelectValue placeholder="All mandates" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">All mandates</SelectItem>
              {(mandates as any[]).map((m) => (
                <SelectItem key={m.id} value={m.id}>{m.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
        <div className="flex gap-1">
          {([7, 30] as const).map((d) => (
            <Button
              key={d}
              size="sm"
              variant={days === d ? 'default' : 'outline'}
              onClick={() => setDays(d)}
            >
              {d}d
            </Button>
          ))}
        </div>
      </div>

      {!tenantId ? (
        <p className="text-muted-foreground text-sm">Select a tenant to view KPI data.</p>
      ) : sumLoading ? (
        <p className="text-muted-foreground text-sm">Loading…</p>
      ) : (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              { label: 'Total KPIs', value: totals.total, cls: '' },
              { label: 'On Track', value: totals.green, cls: 'text-green-600' },
              { label: 'At Risk', value: totals.amber, cls: 'text-amber-600' },
              { label: 'Failing', value: totals.red, cls: 'text-red-600' },
            ].map(({ label, value, cls }) => (
              <Card key={label}>
                <CardContent className="pt-4">
                  <p className="text-xs text-muted-foreground">{label}</p>
                  <p className={`text-2xl font-bold ${cls}`}>{value}</p>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* KPI Gauges */}
          {allKpis.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2">
                  <TrendingUp className="h-4 w-4" />
                  KPI Achievement
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
                  {allKpis.map((kpi, i) => (
                    <KpiGauge key={`${kpi.kpi_name}-${i}`} kpi={kpi} />
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Trend sparkline */}
          {trends.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Spend & Impressions Trend</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={180}>
                  <LineChart data={trends}>
                    <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 10 }} />
                    <Tooltip />
                    <Line
                      type="monotone"
                      dataKey="spend"
                      stroke="#6366f1"
                      dot={false}
                      strokeWidth={2}
                    />
                    <Line
                      type="monotone"
                      dataKey="impressions"
                      stroke="#22c55e"
                      dot={false}
                      strokeWidth={2}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}

          {/* Red Alerts */}
          {redAlerts.length > 0 && (
            <Card className="border-red-200">
              <CardHeader>
                <CardTitle className="text-sm text-red-700 flex items-center gap-2">
                  <AlertCircle className="h-4 w-4" />
                  Failing KPIs — Action Required
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {redAlerts.map((alert) => (
                  <div
                    key={`${alert.activation_id}-${alert.failed_kpi}`}
                    className="flex items-center justify-between rounded-md border border-red-100 bg-red-50 px-3 py-2"
                  >
                    <div>
                      <p className="text-sm font-medium">{alert.channel}</p>
                      <p className="text-xs text-muted-foreground">
                        KPI: {alert.failed_kpi} · Activation: {alert.activation_id}
                      </p>
                    </div>
                    <Button
                      size="sm"
                      variant="destructive"
                      disabled={triggerReplan.isPending}
                      onClick={() => triggerReplan.mutate(alert.campaign_id)}
                    >
                      Replan
                    </Button>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {allKpis.length === 0 && (
            <p className="text-muted-foreground text-sm">No KPI data for this selection.</p>
          )}
        </>
      )}
    </div>
  )
}
