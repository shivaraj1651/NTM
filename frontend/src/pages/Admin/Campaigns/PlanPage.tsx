import { useState, Fragment } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
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
  const { data: planResult, isLoading: planLoading } = useActivationPlan(
    id!,
    campaign?.status === 'confirmed'
  )
  const approveBudget = useApproveBudget(id!)
  const [expanded, setExpanded] = useState<ExpandedState>({})

  const isGenerating = campaign?.status === 'confirmed' && planLoading
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
    { accessorKey: 'channel', header: 'Channel' },
    { accessorKey: 'sub_channel', header: 'Sub-channel' },
    {
      accessorKey: 'budget',
      header: 'Budget',
      cell: ({ row }) =>
        `${row.original.currency} ${row.original.budget.toLocaleString()}`,
    },
    {
      id: 'kpis',
      header: 'KPIs',
      cell: ({ row }) => row.original.kpis.map((k) => k.name).join(', '),
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
    return <p className="text-muted-foreground text-sm">Generating activation plan…</p>
  }

  return (
    <div>
      <h2 className="text-lg font-semibold mb-4">Activation Plan</h2>

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
            {table.getRowModel().rows.length ? (
              table.getRowModel().rows.map((row) => (
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
                        <div className="bg-muted/30 p-4 space-y-3">
                          <div className="grid grid-cols-2 gap-2 text-sm">
                            <div><span className="font-medium">Channel:</span> {row.original.channel}</div>
                            <div><span className="font-medium">Sub-channel:</span> {row.original.sub_channel}</div>
                            <div>
                              <span className="font-medium">Budget:</span>{' '}
                              {row.original.currency} {row.original.budget.toLocaleString()}
                            </div>
                            <div><span className="font-medium">Audience:</span> {row.original.audience}</div>
                          </div>
                          <div>
                            <p className="font-medium text-sm mb-2">KPIs</p>
                            <table className="text-sm w-full">
                              <thead>
                                <tr className="text-left text-muted-foreground">
                                  <th className="pb-1">Name</th>
                                  <th className="pb-1">Target</th>
                                  <th className="pb-1">Unit</th>
                                </tr>
                              </thead>
                              <tbody>
                                {row.original.kpis.map((kpi) => (
                                  <tr key={kpi.name}>
                                    <td>{kpi.name}</td>
                                    <td>{kpi.target}</td>
                                    <td>{kpi.unit}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </Fragment>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="text-center text-muted-foreground py-8">
                  No activations.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {approveBudget.isError && (
        <p className="text-destructive text-sm mb-2">Failed to approve budget. Please try again.</p>
      )}

      <Button onClick={handleApprove} disabled={approveBudget.isPending || activations.length === 0}>
        {approveBudget.isPending ? 'Approving…' : 'Approve Budget'}
      </Button>
    </div>
  )
}
