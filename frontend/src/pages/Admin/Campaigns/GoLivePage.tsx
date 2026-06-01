import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Loader2, CheckCircle2, XCircle, Clock, ExternalLink,
  Rocket, FlaskConical, AlertTriangle,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useCampaign, useGoLive, useActivateCampaign } from '@/hooks/useCampaigns'
import type { PlatformActivationResult } from '@/types/admin'

const PLATFORM_META: Record<string, { label: string; color: string; consoleUrl: (id: string) => string }> = {
  google_ads: {
    label: 'Google Ads',
    color: 'text-blue-600',
    consoleUrl: (id) => `https://ads.google.com/aw/campaigns?campaignId=${id}`,
  },
  meta_ads: {
    label: 'Meta Ads',
    color: 'text-indigo-600',
    consoleUrl: (id) => `https://www.facebook.com/adsmanager/manage/campaigns?act=${id}`,
  },
}

function PlatformCard({
  platform,
  result,
}: {
  platform: string
  result: PlatformActivationResult
}) {
  const meta = PLATFORM_META[platform] ?? { label: platform, color: 'text-gray-600', consoleUrl: () => '#' }
  const isQueued   = result.status === 'queued'
  const isLive     = result.status === 'live' || result.status === 'test_live'
  const isTestLive = result.status === 'test_live'
  const isFailed   = result.status === 'failed'

  return (
    <Card className={`border-l-4 ${isLive ? 'border-l-green-500' : isFailed ? 'border-l-red-500' : 'border-l-amber-400'}`}>
      <CardContent className="pt-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {isQueued && <Loader2 className="h-4 w-4 animate-spin text-amber-500" />}
            {isLive   && <CheckCircle2 className="h-4 w-4 text-green-600" />}
            {isFailed && <XCircle className="h-4 w-4 text-red-600" />}
            <span className={`text-sm font-semibold ${meta.color}`}>{meta.label}</span>
          </div>
          <div className="flex items-center gap-2">
            {isTestLive && (
              <Badge className="bg-amber-100 text-amber-800 border-amber-300 text-xs gap-1">
                <FlaskConical className="h-3 w-3" /> TEST — PAUSED
              </Badge>
            )}
            {isLive && !isTestLive && (
              <Badge className="bg-green-100 text-green-800 border-green-300 text-xs">LIVE</Badge>
            )}
            {isFailed && (
              <Badge variant="destructive" className="text-xs">FAILED</Badge>
            )}
            {isQueued && (
              <Badge className="bg-amber-100 text-amber-700 border-amber-300 text-xs">Launching…</Badge>
            )}
          </div>
        </div>

        {result.campaign_id && (
          <div className="space-y-1 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Campaign ID</span>
              <span className="font-mono">{result.campaign_id}</span>
            </div>
            {result.ad_id && (
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Ad ID</span>
                <span className="font-mono">{result.ad_id}</span>
              </div>
            )}
            {result.ad_set_id && (
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Ad Set ID</span>
                <span className="font-mono">{result.ad_set_id}</span>
              </div>
            )}
          </div>
        )}

        {isLive && result.campaign_id && (
          <a
            href={meta.consoleUrl(result.campaign_id)}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
          >
            Open in {meta.label} <ExternalLink className="h-3 w-3" />
          </a>
        )}

        {isFailed && result.error && (
          <p className="text-xs text-red-600 bg-red-50 rounded p-2 font-mono break-all">
            {result.error}
          </p>
        )}

        {isTestLive && (
          <p className="text-xs text-amber-700 bg-amber-50 rounded p-2">
            Campaign created <strong>PAUSED</strong> — safe for developer testing, no budget spent.
            Activate manually in the ad console when ready for production.
          </p>
        )}
      </CardContent>
    </Card>
  )
}

function CheckItem({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      {ok
        ? <CheckCircle2 className="h-4 w-4 text-green-600 shrink-0" />
        : <Clock className="h-4 w-4 text-muted-foreground shrink-0" />}
      <span className={ok ? '' : 'text-muted-foreground'}>{label}</span>
    </div>
  )
}

export function GoLivePage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: campaign, isError } = useCampaign(id ?? '')
  const goLive   = useGoLive(id ?? '')
  const activate = useActivateCampaign(id ?? '')
  const [launched, setLaunched] = useState(false)

  if (!id) return null
  if (isError) return <p className="text-destructive text-sm">Failed to load campaign.</p>
  if (!campaign) return null

  const { status, creative_assets, activation_plan, activation_results } = campaign

  if (status !== 'creative_ready' && status !== 'live') {
    return <p className="text-muted-foreground text-sm">Campaign is not ready to launch.</p>
  }

  const selectedConcept = campaign.concepts.find(c => c.id === campaign.selected_concept_id)
  const assetCount = creative_assets
    ? creative_assets.copy.length + creative_assets.scripts.length +
      creative_assets.images.length + creative_assets.audio.length
    : 0
  const totalBudget = (activation_plan ?? []).reduce(
    (sum, a) => sum + (a.cost_estimated ?? a.budget ?? 0), 0
  )
  const currency = activation_plan?.[0]?.currency ?? 'USD'

  // Pre-launch checklist
  const hasConceptSelected  = !!campaign.selected_concept_id
  const hasBudgetApproved   = !!campaign.budget_proposal
  const hasCreatives        = assetCount > 0

  // Activation results state
  const resultEntries = Object.entries(activation_results ?? {})
  const allResolved   = resultEntries.length > 0 && resultEntries.every(([, r]) => r.status !== 'queued')
  const anyTestMode   = resultEntries.some(([, r]) => r.test_mode)

  const handleLaunch = async () => {
    try {
      await goLive.mutateAsync()
      await activate.mutateAsync()
      setLaunched(true)
    } catch {
      // errors shown below
    }
  }

  // Post-launch view: show platform results with polling
  if (launched || status === 'live') {
    return (
      <div className="space-y-6 max-w-lg">
        <div className="flex items-center gap-3">
          <div className="rounded-full bg-green-100 p-2">
            <Rocket className="h-5 w-5 text-green-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">Campaign Launched</h2>
            <p className="text-sm text-muted-foreground">
              Platform activation tasks are running.
            </p>
          </div>
          {anyTestMode && (
            <Badge className="ml-auto bg-amber-100 text-amber-800 border-amber-300 gap-1">
              <FlaskConical className="h-3 w-3" /> Developer Test Mode
            </Badge>
          )}
        </div>

        {resultEntries.length === 0 ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Waiting for platform tasks to start…
          </div>
        ) : (
          <div className="space-y-3">
            {resultEntries.map(([platform, result]) => (
              <PlatformCard key={platform} platform={platform} result={result} />
            ))}
          </div>
        )}

        {!allResolved && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="h-3 w-3 animate-spin" />
            Polling for results every 3s…
          </div>
        )}

        {allResolved && (
          <Button onClick={() => navigate(`/campaigns/${id}/kpis`)} variant="outline" size="sm">
            View KPIs →
          </Button>
        )}
      </div>
    )
  }

  // Pre-launch view
  const canLaunch = hasConceptSelected && hasBudgetApproved && hasCreatives
  const isPending = goLive.isPending || activate.isPending

  return (
    <div className="space-y-6 max-w-lg">
      <div className="flex items-center gap-3">
        <div>
          <h2 className="text-lg font-semibold">Go Live</h2>
          <p className="text-sm text-muted-foreground">
            Review the campaign and launch to Google Ads &amp; Meta Ads.
          </p>
        </div>
      </div>

      {/* Pre-launch checklist */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">Pre-Launch Checklist</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <CheckItem label="Concept selected" ok={hasConceptSelected} />
          <CheckItem label="Budget approved" ok={hasBudgetApproved} />
          <CheckItem label={`Creatives ready (${assetCount} assets)`} ok={hasCreatives} />
        </CardContent>
      </Card>

      {/* Campaign summary */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">Campaign Summary</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Concept</span>
            <span className="font-medium">{selectedConcept?.name ?? '—'}</span>
          </div>
          {selectedConcept?.tagline && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">Tagline</span>
              <span className="italic">
                &ldquo;{selectedConcept.tagline}&rdquo;
              </span>
            </div>
          )}
          <div className="flex justify-between">
            <span className="text-muted-foreground">Total Budget</span>
            <span>
              {totalBudget.toLocaleString('en-US', {
                style: 'currency', currency, maximumFractionDigits: 0,
              })}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Creative Assets</span>
            <span>{assetCount}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Platforms</span>
            <span className="flex gap-1">
              <Badge variant="outline" className="text-xs">Google Ads</Badge>
              <Badge variant="outline" className="text-xs">Meta Ads</Badge>
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Test mode notice */}
      <div className="flex items-start gap-2 rounded-md border border-amber-300 bg-amber-50 p-3 text-xs text-amber-800">
        <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
        <div>
          <p className="font-semibold">Developer Test Mode active (NTM_ADS_TEST_MODE=1)</p>
          <p className="mt-0.5">
            Real API calls will be made to Google Ads and Meta Ads.
            Campaigns are created as <strong>PAUSED</strong> with a [TEST] prefix — no budget will be spent.
            Disable NTM_ADS_TEST_MODE to launch live.
          </p>
        </div>
      </div>

      {(goLive.isError || activate.isError) && (
        <p className="text-destructive text-sm">Launch failed — check logs and retry.</p>
      )}

      <Button
        onClick={handleLaunch}
        disabled={!canLaunch || isPending}
        className="w-full sm:w-auto"
      >
        {isPending ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin mr-2" />
            Launching…
          </>
        ) : (
          <>
            <Rocket className="h-4 w-4 mr-2" />
            Launch Campaign
          </>
        )}
      </Button>
    </div>
  )
}
