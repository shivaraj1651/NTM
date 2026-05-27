import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { ColumnDef } from '@tanstack/react-table'
import { PageHeader } from '@/components/PageHeader'
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useAuthStore } from '@/store/useAuthStore'
import { useTenants } from '@/hooks/useTenants'
import { useCampaigns, useCreateCampaign, useMandates, useAllMandates } from '@/hooks/useCampaigns'
import type { Campaign, CampaignStatus } from '@/types/admin'

function statusBadge(status: CampaignStatus) {
  if (status === 'pending') return <Badge variant="secondary">pending</Badge>
  if (status === 'concepts_ready') return <Badge variant="outline">concepts ready</Badge>
  if (status === 'confirmed')
    return <Badge variant="outline" className="border-blue-500 text-blue-600">confirmed</Badge>
  if (status === 'planned')
    return <Badge variant="outline" className="border-blue-500 text-blue-600">planned</Badge>
  if (status === 'budget_proposed')
    return <Badge variant="outline" className="border-amber-500 text-amber-600">budget proposed</Badge>
  return <Badge variant="default">approved</Badge>
}

export function CampaignsPage() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const isAdmin = !!user

  const { data: tenants = [] } = useTenants()
  const [selectedTenantId, setSelectedTenantId] = useState<string | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [selectedMandateId, setSelectedMandateId] = useState<string | null>(null)

  const { data: campaigns = [], isLoading } = useCampaigns(selectedTenantId)
  const { data: mandates = [] } = useMandates(selectedTenantId)
  const { data: allMandates = [] } = useAllMandates()
  const createCampaign = useCreateCampaign()

  const handleCreate = async () => {
    if (!selectedMandateId) return
    const campaign = await createCampaign.mutateAsync(selectedMandateId)
    setSelectedMandateId(null)
    setDialogOpen(false)
    navigate(`/campaigns/${campaign.id}`)
  }

  const columns: ColumnDef<Campaign>[] = [
    {
      accessorKey: 'id',
      header: 'Campaign ID',
      cell: ({ row }) => (
        <span className="font-mono text-xs">{row.original.id}</span>
      ),
    },
    {
      id: 'mandate',
      header: 'Mandate',
      cell: ({ row }) => {
        const mandate = mandates.find((m) => m.id === row.original.mandate_id)
        return mandate?.name ?? row.original.mandate_id
      },
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => statusBadge(row.original.status),
    },
    {
      accessorKey: 'created_at',
      header: 'Created At',
      cell: ({ row }) => new Date(row.original.created_at).toLocaleDateString(),
    },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => (
        <Button
          variant="outline"
          size="sm"
          onClick={() => navigate(`/campaigns/${row.original.id}`)}
        >
          View
        </Button>
      ),
    },
  ]

  return (
    <div>
      <div className="flex items-start justify-between">
        <PageHeader title="Campaigns" description="Manage campaign lifecycle." />
        <Button onClick={() => setDialogOpen(true)} disabled={!selectedTenantId}>
          New Campaign
        </Button>
      </div>

      {isAdmin && (
        <div className="mb-4 w-56">
          <Select onValueChange={setSelectedTenantId}>
            <SelectTrigger>
              <SelectValue placeholder="Select tenant…" />
            </SelectTrigger>
            <SelectContent>
              {(tenants as { id: string; name: string }[]).map((t) => (
                <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      {!selectedTenantId ? (
        <p className="text-muted-foreground text-sm">Select a tenant to view campaigns.</p>
      ) : isLoading ? (
        <p className="text-muted-foreground text-sm">Loading…</p>
      ) : (
        <DataTable columns={columns} data={campaigns} />
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New Campaign</DialogTitle>
          </DialogHeader>
          <div className="py-2">
            <Select onValueChange={setSelectedMandateId}>
              <SelectTrigger>
                <SelectValue placeholder="Select mandate…" />
              </SelectTrigger>
              <SelectContent>
                {allMandates.map((m) => (
                  <SelectItem key={m.id} value={m.id}>
                    {m.name} — {m.budget.currency} {m.budget.total_budget.toLocaleString()}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button
              onClick={handleCreate}
              disabled={!selectedMandateId || createCampaign.isPending}
            >
              {createCampaign.isPending ? 'Creating…' : 'Create'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
