import { useState } from 'react'
import type { ColumnDef } from '@tanstack/react-table'
import { PageHeader } from '@/components/PageHeader'
import { DataTable } from '@/components/data-table'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { useAudit } from '@/hooks/useAudit'
import type { AuditEntry, AuditFilters } from '@/types/admin'

const ENTITY_TYPES = ['tenant', 'user', 'role']

export function AuditLogPage() {
  const [draft, setDraft] = useState<AuditFilters>({})
  const [applied, setApplied] = useState<AuditFilters>({})
  const { data: entries = [], isLoading } = useAudit(applied)

  const columns: ColumnDef<AuditEntry>[] = [
    {
      accessorKey: 'timestamp',
      header: 'Timestamp',
      cell: ({ row }) => new Date(row.original.timestamp).toLocaleString(),
    },
    { accessorKey: 'actor', header: 'Actor' },
    {
      accessorKey: 'action',
      header: 'Action',
      cell: ({ row }) => (
        <Badge variant="outline" className="text-xs font-mono">{row.original.action}</Badge>
      ),
    },
    { accessorKey: 'entity_type', header: 'Entity Type' },
    { accessorKey: 'entity_id',   header: 'Entity ID' },
    { accessorKey: 'detail',      header: 'Detail' },
  ]

  return (
    <div>
      <PageHeader title="Audit Log" description="Filterable history of all admin actions." />

      <div className="flex flex-wrap gap-3 mb-4">
        <Select
          onValueChange={(v) => setDraft({ ...draft, entity_type: v === 'all' ? undefined : v })}
        >
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Entity type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All types</SelectItem>
            {ENTITY_TYPES.map((t) => (
              <SelectItem key={t} value={t}>{t}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Input
          placeholder="Actor email"
          className="w-48"
          value={draft.actor ?? ''}
          onChange={(e) => setDraft({ ...draft, actor: e.target.value || undefined })}
        />

        <Input
          type="date"
          className="w-40"
          value={draft.from ?? ''}
          onChange={(e) => setDraft({ ...draft, from: e.target.value || undefined })}
        />
        <Input
          type="date"
          className="w-40"
          value={draft.to ?? ''}
          onChange={(e) => setDraft({ ...draft, to: e.target.value || undefined })}
        />

        <Button onClick={() => setApplied({ ...draft })}>Apply</Button>
        <Button variant="outline" onClick={() => { setDraft({}); setApplied({}) }}>Reset</Button>
      </div>

      {isLoading ? (
        <p className="text-muted-foreground text-sm">Loading…</p>
      ) : (
        <DataTable columns={columns} data={entries} />
      )}
    </div>
  )
}
