import { useParams, useNavigate } from 'react-router-dom'
import { PageHeader } from '@/components/PageHeader'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useMandateSummary, useConfirmMandate } from '@/hooks/useMandates'
import type { MandateStatus } from '@/types/admin'

function statusBadge(status: MandateStatus) {
  if (status === 'confirmed') return <Badge variant="default">Confirmed</Badge>
  if (status === 'rejected') return <Badge variant="destructive">Rejected</Badge>
  if (status === 'draft') return <Badge variant="secondary">Draft</Badge>
  return <Badge variant="outline">Pending Review</Badge>
}

export function MandateSummaryPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: mandate, isLoading, isError } = useMandateSummary(id!)
  const confirm = useConfirmMandate(id!)

  if (isLoading) return <p className="text-muted-foreground text-sm">Loading…</p>
  if (isError || !mandate) return <p className="text-destructive text-sm">Failed to load mandate.</p>

  const isConfirmed = mandate.status === 'confirmed'

  const handleConfirm = async () => {
    const campaign = await confirm.mutateAsync()
    navigate(`/admin/campaigns/${campaign.id}`)
  }

  return (
    <div>
      <PageHeader title="Mandate Summary" description="Review and confirm the mandate." />
      <Card className="max-w-2xl">
        <CardContent className="pt-6 space-y-4">
          <div className="flex items-start justify-between">
            <h2 className="text-lg font-semibold">{mandate.name}</h2>
            {statusBadge(mandate.status)}
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="font-medium">Objective:</span>{' '}
              <span className="capitalize">{mandate.objective}</span>
            </div>
            <div><span className="font-medium">Region:</span> {mandate.region}</div>
            <div className="col-span-2">
              <span className="font-medium">Countries:</span>{' '}
              {mandate.countries.join(', ')}
            </div>
            <div>
              <span className="font-medium">Budget:</span>{' '}
              {mandate.budget.currency} {mandate.budget.total_budget.toLocaleString()}
            </div>
            <div>
              <span className="font-medium">Duration:</span>{' '}
              {mandate.start_date} → {mandate.end_date}
            </div>
            <div>
              <span className="font-medium">Client:</span> {mandate.client.org_name}
            </div>
            <div>
              <span className="font-medium">Industry:</span> {mandate.client.industry}
            </div>
            <div className="col-span-2">
              <span className="font-medium">Competitors:</span>{' '}
              <span className="flex flex-wrap gap-1 mt-1">
                {mandate.client.competitors.map((c) => (
                  <Badge key={c} variant="secondary" className="text-xs">{c}</Badge>
                ))}
              </span>
            </div>
          </div>
          <div className="flex gap-2 pt-2">
            <Button
              variant="outline"
              onClick={() => navigate(`/admin/mandates/${id}/edit`)}
              disabled={isConfirmed || confirm.isPending}
            >
              Reject
            </Button>
            <Button onClick={handleConfirm} disabled={isConfirmed || confirm.isPending}>
              {confirm.isPending ? 'Confirming…' : 'Confirm →'}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
