import { useState } from 'react'
import { FileText, RefreshCw, AlertCircle, Download } from 'lucide-react'
import { PageHeader } from '@/components/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useAuthStore } from '@/store/useAuthStore'
import { useCampaigns } from '@/hooks/useCampaigns'
import { useCampaignReport, useGenerateCampaignReport } from '@/hooks/useReports'

function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-bold">{value}</p>
      </CardContent>
    </Card>
  )
}

function ReportSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  )
}

function renderJsonValue(val: unknown): string {
  if (val === null || val === undefined) return '—'
  if (typeof val === 'number') return val.toLocaleString()
  if (typeof val === 'boolean') return val ? 'Yes' : 'No'
  if (typeof val === 'string') return val
  return JSON.stringify(val, null, 2)
}

export function ReportsPage() {
  const { user } = useAuthStore()
  const tenantId = user?.tenant_id ?? null

  const { data: campaigns = [], isLoading: campaignsLoading } = useCampaigns(tenantId)
  const [selectedCampaignId, setSelectedCampaignId] = useState<string | null>(null)

  const {
    data: report,
    isLoading: reportLoading,
    error: reportError,
    isError,
  } = useCampaignReport(selectedCampaignId)

  const generate = useGenerateCampaignReport(selectedCampaignId ?? '')
  const [generateState, setGenerateState] = useState<'idle' | 'queued' | 'error'>('idle')

  const handleGenerate = async () => {
    if (!selectedCampaignId) return
    try {
      await generate.mutateAsync()
      setGenerateState('queued')
      setTimeout(() => setGenerateState('idle'), 4000)
    } catch {
      setGenerateState('error')
      setTimeout(() => setGenerateState('idle'), 3000)
    }
  }

  const selectedCampaign = campaigns.find((c: any) => c.id === selectedCampaignId)

  const reportJson = report?.report_json ?? {}
  const topLevelMetrics = Object.entries(reportJson).filter(
    ([, v]) => typeof v !== 'object' || v === null
  )
  const topLevelSections = Object.entries(reportJson).filter(
    ([, v]) => typeof v === 'object' && v !== null
  )

  const handleExport = () => {
    if (!report) return
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `report-${selectedCampaignId}-${report.period_start}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const is404 = isError && (reportError as any)?.response?.status === 404

  return (
    <div className="space-y-6">
      <PageHeader
        title="Reports"
        description="Generate and view campaign performance reports."
      />

      {/* Campaign selector + actions */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="w-72">
          {campaignsLoading ? (
            <p className="text-sm text-muted-foreground">Loading campaigns…</p>
          ) : (
            <Select
              value={selectedCampaignId ?? ''}
              onValueChange={(v) => {
                setSelectedCampaignId(v || null)
                setGenerateState('idle')
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select a campaign…" />
              </SelectTrigger>
              <SelectContent>
                {campaigns.length === 0 ? (
                  <SelectItem value="__none" disabled>
                    No campaigns found
                  </SelectItem>
                ) : (
                  campaigns.map((c: any) => (
                    <SelectItem key={c.id} value={c.id}>
                      {c.id.slice(0, 8)}…{' '}
                      <span className="text-muted-foreground text-xs ml-1">({c.status})</span>
                    </SelectItem>
                  ))
                )}
              </SelectContent>
            </Select>
          )}
        </div>

        {selectedCampaignId && (
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={handleGenerate}
              disabled={generate.isPending || generateState === 'queued'}
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              {generateState === 'queued'
                ? 'Queued ✓'
                : generateState === 'error'
                ? 'Failed — retry'
                : 'Generate Report'}
            </Button>

            {report && (
              <Button variant="ghost" size="sm" onClick={handleExport}>
                <Download className="h-4 w-4 mr-2" />
                Export JSON
              </Button>
            )}
          </>
        )}
      </div>

      {/* No campaign selected */}
      {!selectedCampaignId && (
        <div className="flex flex-col items-center justify-center py-20 text-muted-foreground gap-3">
          <FileText className="h-10 w-10 opacity-30" />
          <p className="text-sm">Select a campaign above to view its report.</p>
        </div>
      )}

      {/* Loading */}
      {selectedCampaignId && reportLoading && (
        <p className="text-sm text-muted-foreground">Loading report…</p>
      )}

      {/* No report yet */}
      {selectedCampaignId && is404 && (
        <div className="flex items-start gap-3 rounded-md border border-amber-300 bg-amber-50 p-4 text-sm text-amber-800">
          <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
          <div>
            <p className="font-medium">No report generated yet</p>
            <p className="text-xs mt-0.5">
              Click <strong>Generate Report</strong> to create the first daily report for this
              campaign.
            </p>
          </div>
        </div>
      )}

      {/* Other errors */}
      {selectedCampaignId && isError && !is404 && (
        <div className="flex items-start gap-3 rounded-md border border-red-300 bg-red-50 p-4 text-sm text-red-800">
          <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
          <p>Failed to load report. Please try again.</p>
        </div>
      )}

      {/* Report content */}
      {report && !reportLoading && (
        <div className="space-y-6">
          {/* Report metadata */}
          <div className="flex flex-wrap items-center gap-3">
            <Badge variant="outline" className="capitalize">
              {report.report_type} report
            </Badge>
            <span className="text-sm text-muted-foreground">
              Period: {report.period_start} → {report.period_end}
            </span>
            {selectedCampaign && (
              <Badge variant="secondary" className="capitalize">
                {selectedCampaign.status}
              </Badge>
            )}
          </div>

          {/* Top-level scalar metrics */}
          {topLevelMetrics.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {topLevelMetrics.map(([key, val]) => (
                <MetricCard
                  key={key}
                  label={key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                  value={renderJsonValue(val)}
                />
              ))}
            </div>
          )}

          {/* Nested sections */}
          {topLevelSections.map(([key, val]) => (
            <ReportSection
              key={key}
              title={key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
            >
              {Array.isArray(val) ? (
                val.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No data.</p>
                ) : typeof val[0] === 'object' ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b">
                          {Object.keys(val[0] as Record<string, unknown>).map((col) => (
                            <th
                              key={col}
                              className="text-left py-2 pr-4 text-muted-foreground font-medium text-xs uppercase tracking-wide"
                            >
                              {col.replace(/_/g, ' ')}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {(val as Record<string, unknown>[]).map((row, i) => (
                          <tr key={i} className="border-b last:border-0">
                            {Object.values(row).map((cell, j) => (
                              <td key={j} className="py-2 pr-4 text-xs">
                                {renderJsonValue(cell)}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <ul className="text-sm space-y-1">
                    {(val as unknown[]).map((item, i) => (
                      <li key={i} className="text-muted-foreground">
                        {renderJsonValue(item)}
                      </li>
                    ))}
                  </ul>
                )
              ) : (
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {Object.entries(val as Record<string, unknown>).map(([k, v]) => (
                    <div key={k}>
                      <span className="text-muted-foreground text-xs uppercase tracking-wide">
                        {k.replace(/_/g, ' ')}
                      </span>
                      <p className="font-medium">{renderJsonValue(v)}</p>
                    </div>
                  ))}
                </div>
              )}
            </ReportSection>
          ))}

          {/* Empty report */}
          {topLevelMetrics.length === 0 && topLevelSections.length === 0 && (
            <p className="text-sm text-muted-foreground">
              Report was generated but contains no data yet.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
