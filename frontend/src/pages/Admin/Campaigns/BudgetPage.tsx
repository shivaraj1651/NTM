import { useParams, useNavigate } from 'react-router-dom'
import type { ColumnDef } from '@tanstack/react-table'
import { Loader2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { DataTable } from '@/components/data-table'
import { Button } from '@/components/ui/button'
import { useCampaign, useConfirmBudget } from '@/hooks/useCampaigns'
import type { BudgetAllocation } from '@/types/admin'

export function BudgetPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  // Poll while budget is being generated (budget_pending) or AGT-05 still running (planned, no proposal yet)
  const { data: campaign, isLoading } = useCampaign(id!)
  const confirmBudget = useConfirmBudget(id!)

  if (isLoading) return <p className="text-muted-foreground text-sm">Loading…</p>
  if (!campaign) return null
  if (campaign?.status === 'budget_pending') return <p className="text-muted-foreground text-sm">Generating budget…</p>

  const { budget_proposal, status } = campaign

  if (status === 'planned' && !budget_proposal) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground text-sm">
        <Loader2 className="h-4 w-4 animate-spin" />
        Budget optimisation in progress…
      </div>
    )
  }

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
        <Button
          onClick={() =>
            confirmBudget.mutate(undefined, {
              onSuccess: () => navigate(`/campaigns/${id}/creatives`),
            })
          }
          disabled={confirmBudget.isPending}
        >
          {confirmBudget.isPending ? 'Confirming…' : 'Confirm Budget'}
        </Button>
      )}
    </div>
  )
}
