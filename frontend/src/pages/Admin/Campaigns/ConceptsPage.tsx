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
    navigate(`/campaigns/${id}/plan`)
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
