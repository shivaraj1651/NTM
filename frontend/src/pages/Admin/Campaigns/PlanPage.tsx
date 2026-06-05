import { useState, Fragment } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
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
  const { data: planResult } = useActivationPlan(
    id!,
    campaign?.status === 'confirmed'
  )
  const approveBudget = useApproveBudget(id!)
  const [expanded, setExpanded] = useState<ExpandedState>({})

  const isGenerating = campaign?.status === 'confirmed'
  const activations = (planResult ?? campaign)?.activation_plan ?? []

  const handleApprove = async () => {
    await approveBudget.mutateAsync()
    navigate(`/campaigns/${id}/budget`)
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
    {
      id: 'channel',
      header: 'Channel',
      cell: ({ row }) => row.original.sub_channel || row.original.channel || '—',
    },
    {
      id: 'geography',
      header: 'Geography',
      cell: ({ row }) => row.original.geography || '—',
    },
    {
      id: 'phase',
      header: 'Phase',
      cell: ({ row }) => row.original.phase || '—',
    },
    {
      id: 'reach',
      header: 'Est. Reach',
      cell: ({ row }) =>
        row.original.estimated_reach
          ? row.original.estimated_reach.toLocaleString()
          : '—',
    },
    {
      id: 'cost',
      header: 'Est. Cost',
      cell: ({ row }) => {
        const cost = row.original.cost_estimated ?? row.original.budget
        return cost != null ? cost.toLocaleString(undefined, { maximumFractionDigits: 0 }) : '—'
      },
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
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <div className="text-center">
          <p className="font-semibold text-base">Activation Plan is Generating…</p>
          <p className="text-sm text-muted-foreground mt-1">This may take up to 60 seconds.</p>
        </div>
      </div>
    )
  }

  return (
    <div>
      <h2 className="text-lg font-semibold mb-4">Activation Plan</h2>

      {activations.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 gap-3">
          <p className="font-semibold text-base text-destructive">No activation plan was generated.</p>
          <p className="text-sm text-muted-foreground">
            The media planner returned no activations. This can happen when the mandate has no
            budget or geography data.
          </p>
          <Button variant="outline" onClick={() => window.location.reload()}>
            Retry
          </Button>
        </div>
      ) : (
        <>
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
                {table.getRowModel().rows.map((row) => (
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
                          <div className="bg-muted/30 p-4 space-y-2 text-sm">
                            <div className="grid grid-cols-2 gap-2">
                              <div><span className="font-medium">Channel:</span> {row.original.sub_channel || row.original.channel || '—'}</div>
                              <div><span className="font-medium">Geography:</span> {row.original.geography || '—'}</div>
                              <div><span className="font-medium">Phase:</span> {row.original.phase || '—'}</div>
                              <div><span className="font-medium">Audience Segment:</span> {row.original.audience_segment || row.original.audience || '—'}</div>
                              <div><span className="font-medium">Placement:</span> {row.original.placement || '—'}</div>
                              <div><span className="font-medium">Format:</span> {row.original.format || '—'}</div>
                              <div><span className="font-medium">Frequency:</span> {(row.original as any).frequency || '—'}</div>
                              <div><span className="font-medium">CPM:</span> {row.original.estimated_cpm != null ? `$${row.original.estimated_cpm}` : '—'}</div>
                            </div>
                          </div>
                        </TableCell>
                      </TableRow>
                    )}
                  </Fragment>
                ))}
              </TableBody>
            </Table>
          </div>

          {approveBudget.isError && (
            <p className="text-destructive text-sm mb-2">Failed to approve budget. Please try again.</p>
          )}

          <Button onClick={handleApprove} disabled={approveBudget.isPending}>
            {approveBudget.isPending ? 'Approving…' : 'Approve Budget'}
          </Button>
        </>
      )}
    </div>
  )
}
