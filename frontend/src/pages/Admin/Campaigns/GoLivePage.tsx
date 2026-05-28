import { useParams, useNavigate } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useCampaign, useGoLive, useActivateCampaign } from '@/hooks/useCampaigns'

export function GoLivePage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: campaign, isError } = useCampaign(id ?? '')
  const goLive = useGoLive(id ?? '')
  const activate = useActivateCampaign(id ?? '')

  if (!id) return null
  if (isError) return <p className="text-destructive text-sm">Failed to load campaign.</p>
  if (!campaign) return null

  if (campaign.status !== 'creative_ready') {
    return <p className="text-muted-foreground text-sm">Campaign is not ready to launch.</p>
  }

  const totalBudget = campaign.activation_plan.reduce((sum, a) => sum + a.budget, 0)
  const currency = campaign.activation_plan[0]?.currency ?? 'USD'
  const selectedConcept = campaign.concepts.find(
    (c) => c.id === campaign.selected_concept_id
  )
  const assets = campaign.creative_assets
  const assetCount = assets
    ? assets.copy.length + assets.scripts.length + assets.images.length + assets.audio.length
    : 0

  const handleLaunch = async () => {
    try {
      await goLive.mutateAsync()
      // Dispatch platform activation tasks (AGT-12) after status is set to live
      await activate.mutateAsync()
      navigate(`/campaigns/${id}/kpis`)
    } catch {
      // Errors stored in goLive.isError / activate.isError, displayed in UI
    }
  }

  return (
    <div className="space-y-6 max-w-lg">
      <div>
        <h2 className="text-lg font-semibold">Go Live</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Review the campaign summary and launch when ready.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Campaign Summary</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Campaign ID</span>
            <span className="font-mono">{id}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Concept</span>
            <span>{selectedConcept?.name ?? '—'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Total Budget</span>
            <span>
              {totalBudget.toLocaleString('en-US', {
                style: 'currency',
                currency,
                maximumFractionDigits: 0,
              })}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Creative Assets</span>
            <span>{assetCount}</span>
          </div>
        </CardContent>
      </Card>

      {(goLive.isError || activate.isError) && (
        <p className="text-destructive text-sm">Launch failed. Please try again.</p>
      )}

      <Button
        onClick={handleLaunch}
        disabled={goLive.isPending || activate.isPending}
        className="w-full sm:w-auto"
      >
        {(goLive.isPending || activate.isPending) ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin mr-2" />
            Launching…
          </>
        ) : (
          'Launch Campaign'
        )}
      </Button>
    </div>
  )
}
