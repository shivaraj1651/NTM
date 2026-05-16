import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { Pencil } from 'lucide-react'
import type { ColumnDef } from '@tanstack/react-table'
import { DataTable } from '@/components/data-table'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useCampaignKpis, useUpdateKpiConfig } from '@/hooks/useCampaigns'
import type { CampaignKpiRow } from '@/types/admin'

function statusColor(status: CampaignKpiRow['status']) {
  if (status === 'green') return 'text-green-600'
  if (status === 'amber') return 'text-amber-600'
  return 'text-red-600'
}

function StatusBadge({ status }: { status: CampaignKpiRow['status'] }) {
  if (status === 'green') return <Badge className="bg-green-600 text-white">Green</Badge>
  if (status === 'amber') return <Badge variant="outline" className="border-amber-400 text-amber-600">Amber</Badge>
  return <Badge variant="destructive">Red</Badge>
}

interface EditDialogProps {
  row: CampaignKpiRow | null
  onClose: () => void
  onSave: (activationId: string, kpiName: string, values: { target: number; green_threshold: number; amber_threshold: number }) => void
  isPending: boolean
}

function EditDialog({ row, onClose, onSave, isPending }: EditDialogProps) {
  const [target, setTarget] = useState(String(row?.target ?? ''))
  const [green, setGreen] = useState(String(row?.green_threshold ?? ''))
  const [amber, setAmber] = useState(String(row?.amber_threshold ?? ''))
  const [error, setError] = useState<string | null>(null)

  if (!row) return null

  const handleSave = () => {
    const t = Number(target)
    const g = Number(green)
    const a = Number(amber)
    if (isNaN(t) || isNaN(g) || isNaN(a)) {
      setError('All fields must be valid numbers.')
      return
    }
    if (g < 0 || g > 100 || a < 0 || a > 100) {
      setError('Thresholds must be between 0 and 100.')
      return
    }
    if (a >= g) {
      setError('Amber threshold must be less than green threshold.')
      return
    }
    setError(null)
    onSave(row.activation_id, row.kpi_name, { target: t, green_threshold: g, amber_threshold: a })
  }

  return (
    <Dialog open={!!row} onOpenChange={(open) => { if (!open) onClose() }}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Edit KPI — {row.kpi_name}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-1">
            <Label>Target ({row.unit})</Label>
            <Input
              type="number"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label>Green threshold %</Label>
            <Input
              type="number"
              value={green}
              onChange={(e) => setGreen(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label>Amber threshold %</Label>
            <Input
              type="number"
              value={amber}
              onChange={(e) => setAmber(e.target.value)}
            />
          </div>
          {error && <p className="text-destructive text-sm">{error}</p>}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSave} disabled={isPending}>Save</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export function KpisPage() {
  const { id } = useParams<{ id: string }>()
  const { data: rows, isLoading, isError } = useCampaignKpis(id ?? '')
  const updateKpiConfig = useUpdateKpiConfig(id ?? '')
  const [editRow, setEditRow] = useState<CampaignKpiRow | null>(null)

  if (!id) return null

  const columns: ColumnDef<CampaignKpiRow>[] = [
    { accessorKey: 'channel', header: 'Channel' },
    { accessorKey: 'sub_channel', header: 'Sub-channel' },
    { accessorKey: 'kpi_name', header: 'KPI' },
    { accessorKey: 'unit', header: 'Unit' },
    { accessorKey: 'target', header: 'Target' },
    { accessorKey: 'actual', header: 'Actual' },
    {
      id: 'achievement',
      header: 'Achievement',
      cell: ({ row }: { row: any }) => (
        <span className={statusColor(row.original.status)}>
          {row.original.achievement_percent}%
        </span>
      ),
    },
    {
      id: 'status',
      header: 'Status',
      cell: ({ row }: { row: any }) => <StatusBadge status={row.original.status} />,
    },
    {
      id: 'edit',
      header: '',
      cell: ({ row }: { row: any }) => (
        <Button variant="ghost" size="sm" onClick={() => setEditRow(row.original)}>
          <Pencil className="h-4 w-4" />
        </Button>
      ),
    },
  ]

  if (isLoading) return <p className="text-muted-foreground text-sm">Loading…</p>
  if (isError) return <p className="text-destructive text-sm">Failed to load KPI data.</p>

  return (
    <div>
      <h2 className="text-lg font-semibold mb-4">KPI Tracking</h2>
      {!rows || rows.length === 0 ? (
        <p className="text-muted-foreground text-sm">No KPI data available.</p>
      ) : (
        <DataTable columns={columns} data={rows} />
      )}
      <EditDialog
        row={editRow}
        onClose={() => setEditRow(null)}
        onSave={(activationId, kpiName, values) => {
          updateKpiConfig.mutate(
            { activationId, kpiName, ...values },
            { onSuccess: () => setEditRow(null) }
          )
        }}
        isPending={updateKpiConfig.isPending}
      />
    </div>
  )
}
