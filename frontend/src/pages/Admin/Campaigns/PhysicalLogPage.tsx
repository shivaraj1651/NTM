import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import type { ColumnDef } from '@tanstack/react-table'
import { apiClient } from '@/api/client'
import { DataTable } from '@/components/data-table'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'

interface PhysicalLog {
  id: string
  activation_id: string | null
  event_type: string
  channel: string
  payload: {
    actual_run_date?: string
    actual_cost?: number
    vendor_name?: string
    grp_circulation?: string
    proof_urls?: string[]
    notes?: string
  }
  logged_at: string
}

interface LogForm {
  channel: string
  actual_run_date: string
  actual_cost: string
  vendor_name: string
  grp_circulation: string
  notes: string
}

const EMPTY_FORM: LogForm = {
  channel: '',
  actual_run_date: '',
  actual_cost: '',
  vendor_name: '',
  grp_circulation: '',
  notes: '',
}

function useCampaignPhysicalLogs(campaignId: string) {
  return useQuery<PhysicalLog[]>({
    queryKey: ['physical-logs', campaignId],
    queryFn: () =>
      apiClient.get(`/activations/${campaignId}/physical-logs`).then((r) => r.data),
    enabled: !!campaignId,
  })
}

function useLogPhysicalActivation(campaignId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: object) =>
      apiClient.post(`/activations/${campaignId}/log-physical`, body).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['physical-logs', campaignId] }),
  })
}

const columns: ColumnDef<PhysicalLog>[] = [
  { accessorKey: 'channel', header: 'Channel' },
  { accessorKey: 'event_type', header: 'Event' },
  {
    id: 'vendor',
    header: 'Vendor',
    cell: ({ row }) => row.original.payload.vendor_name ?? '—',
  },
  {
    id: 'run_date',
    header: 'Run Date',
    cell: ({ row }) => row.original.payload.actual_run_date ?? '—',
  },
  {
    id: 'cost',
    header: 'Actual Cost',
    cell: ({ row }) => {
      const cost = row.original.payload.actual_cost
      return cost != null ? `₹${cost.toLocaleString()}` : '—'
    },
  },
  {
    id: 'grp',
    header: 'GRP / Circ.',
    cell: ({ row }) => row.original.payload.grp_circulation ?? '—',
  },
  {
    id: 'proofs',
    header: 'Proofs',
    cell: ({ row }) => {
      const urls = row.original.payload.proof_urls ?? []
      return urls.length > 0 ? (
        <Badge variant="secondary">{urls.length} file{urls.length > 1 ? 's' : ''}</Badge>
      ) : (
        <span className="text-muted-foreground text-xs">None</span>
      )
    },
  },
  {
    id: 'logged_at',
    header: 'Logged At',
    cell: ({ row }) => new Date(row.original.logged_at).toLocaleString(),
  },
]

export function PhysicalLogPage() {
  const { id } = useParams<{ id: string }>()
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState<LogForm>(EMPTY_FORM)

  const { data: logs = [], isLoading } = useCampaignPhysicalLogs(id ?? '')
  const logMutation = useLogPhysicalActivation(id ?? '')

  if (!id) return null

  const handleSubmit = () => {
    logMutation.mutate(
      {
        campaign_id: id,
        channel: form.channel,
        event_type: 'proof_of_execution',
        actual_run_date: form.actual_run_date || null,
        actual_cost: form.actual_cost ? parseFloat(form.actual_cost) : null,
        vendor_name: form.vendor_name || null,
        grp_circulation: form.grp_circulation || null,
        notes: form.notes || null,
        proof_urls: [],
      },
      {
        onSuccess: () => {
          setOpen(false)
          setForm(EMPTY_FORM)
        },
      },
    )
  }

  const field = (key: keyof LogForm, label: string, placeholder?: string) => (
    <div className="space-y-1">
      <Label>{label}</Label>
      <Input
        value={form[key]}
        onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
        placeholder={placeholder}
      />
    </div>
  )

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Physical Activation Log</h2>
        <Button size="sm" onClick={() => setOpen(true)}>
          <Plus className="h-4 w-4 mr-1" />
          Log Activation
        </Button>
      </div>

      {isLoading ? (
        <p className="text-muted-foreground text-sm">Loading…</p>
      ) : logs.length === 0 ? (
        <p className="text-muted-foreground text-sm">No physical activations logged yet.</p>
      ) : (
        <DataTable columns={columns} data={logs} />
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Log Physical Activation</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            {field('channel', 'Channel *', 'e.g. Print, OOH, Radio')}
            {field('actual_run_date', 'Actual Run Date', 'YYYY-MM-DD')}
            {field('actual_cost', 'Actual Cost (₹)', '0')}
            {field('vendor_name', 'Vendor Name', 'Times of India, Big FM…')}
            {field('grp_circulation', 'GRP / Circulation', 'e.g. 45 GRP or 500,000 copies')}
            {field('notes', 'Notes')}
          </div>
          {logMutation.isError && (
            <p className="text-destructive text-sm">Failed to save. Please try again.</p>
          )}
          <div className="flex gap-2 justify-end pt-2">
            <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button
              onClick={handleSubmit}
              disabled={!form.channel || logMutation.isPending}
            >
              {logMutation.isPending ? 'Saving…' : 'Save'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
