import { useState } from 'react'
import type { ColumnDef } from '@tanstack/react-table'
import { PageHeader } from '@/components/PageHeader'
import { DataTable } from '@/components/data-table'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useAudit } from '@/hooks/useAudit'
import type { AuditEntry, AuditFilters } from '@/types/admin'

// Note: backend GET /admin/audit-log only supports tenant_id, limit, offset filters.
// entity_type, actor, date-range filters are client-side only.

export function AuditLogPage() {
  const [tenantId, setTenantId] = useState<string>('')
  const [applied, setApplied] = useState<AuditFilters>({})
  const { data: entries = [], isLoading } = useAudit(applied)

  const columns: ColumnDef<AuditEntry>[] = [
    {
      accessorKey: 'created_at',
      header: 'Timestamp',
      cell: ({ row }) => new Date(row.original.created_at).toLocaleString(),
    },
    { accessorKey: 'actor_id', header: 'Actor' },
    {
      accessorKey: 'action',
      header: 'Action',
      cell: ({ row }) => (
        <Badge variant="outline" className="text-xs font-mono">{row.original.action}</Badge>
      ),
    },
    { accessorKey: 'entity_type', header: 'Entity Type' },
    { accessorKey: 'entity_id',   header: 'Entity ID' },
    { accessorKey: 'notes',       header: 'Notes' },
  ]

  return (
    <div>
      <PageHeader title="Audit Log" description="Filterable history of all admin actions." />

      <div className="flex flex-wrap gap-3 mb-4">
        <Input
          placeholder="Tenant ID (optional)"
          className="w-64"
          value={tenantId}
          onChange={(e) => setTenantId(e.target.value)}
        />

        <Button onClick={() => setApplied({ tenant_id: tenantId || undefined })}>Apply</Button>
        <Button variant="outline" onClick={() => { setTenantId(''); setApplied({}) }}>Reset</Button>
      </div>

      {isLoading ? (
        <p className="text-muted-foreground text-sm">Loading…</p>
      ) : (
        <DataTable columns={columns} data={entries} />
      )}
    </div>
  )
}
