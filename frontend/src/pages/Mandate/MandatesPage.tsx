import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { ColumnDef } from '@tanstack/react-table'
import { PageHeader } from '@/components/PageHeader'
import { DataTable } from '@/components/data-table'
import { Button } from '@/components/ui/button'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { useAuthStore } from '@/store/useAuthStore'
import { useTenants } from '@/hooks/useTenants'
import { useMandateList } from '@/hooks/useMandates'
import { MandateStatusBadge } from '@/lib/mandate-utils'
import type { MandateSummaryCard } from '@/types/admin'

export function MandatesPage() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const isAdmin = !!user
  const { data: tenants = [] } = useTenants()
  const [selectedTenantId, setSelectedTenantId] = useState<string | null>(null)

  const { data: mandates = [], isLoading } = useMandateList(selectedTenantId)

  const columns: ColumnDef<MandateSummaryCard>[] = [
    {
      accessorKey: 'name',
      header: 'Name',
    },
    {
      accessorKey: 'objective',
      header: 'Objective',
      cell: ({ row }) => <span className="capitalize">{row.original.objective}</span>,
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => <MandateStatusBadge status={row.original.status} />,
    },
    {
      accessorKey: 'created_at',
      header: 'Created',
      cell: ({ row }) => new Date(row.original.created_at).toLocaleDateString(),
    },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => (
        <Button
          variant="outline"
          size="sm"
          onClick={() => navigate(`/admin/mandates/${row.original.id}/summary`)}
        >
          View
        </Button>
      ),
    },
  ]

  return (
    <div>
      <div className="flex items-start justify-between">
        <PageHeader title="Mandates" description="Manage client mandates." />
        <Button onClick={() => navigate('/onboarding')}>New Mandate</Button>
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
        <p className="text-muted-foreground text-sm">Select a tenant to view mandates.</p>
      ) : isLoading ? (
        <p className="text-muted-foreground text-sm">Loading…</p>
      ) : (
        <DataTable columns={columns} data={mandates} />
      )}
    </div>
  )
}
