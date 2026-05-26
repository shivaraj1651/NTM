import type { ColumnDef } from '@tanstack/react-table'
import { PageHeader } from '@/components/PageHeader'
import { DataTable } from '@/components/data-table'
import { Badge } from '@/components/ui/badge'
import { RoleBadge } from '@/components/RoleBadge'
import { useRoles } from '@/hooks/useRoles'
import type { Role } from '@/types/admin'

export function RolesPage() {
  const { data: roles = [], isLoading } = useRoles()

  const columns: ColumnDef<Role>[] = [
    {
      accessorKey: 'name',
      header: 'Role',
      cell: ({ row }) => <RoleBadge role={row.original.name} />,
    },
    {
      accessorKey: 'permissions',
      header: 'Permissions',
      cell: ({ row }) => (
        <div className="flex flex-wrap gap-1">
          {row.original.permissions.map((p) => (
            <Badge key={p} variant="outline" className="text-xs">{p}</Badge>
          ))}
        </div>
      ),
    },
    {
      accessorKey: 'user_count',
      header: 'Users',
      cell: ({ row }) => (
        <span className="text-muted-foreground">{row.original.user_count}</span>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="Roles"
        description="Platform roles and their permissions. Roles are fixed and cannot be edited."
      />
      {isLoading ? (
        <p className="text-muted-foreground text-sm">Loading…</p>
      ) : (
        <DataTable columns={columns} data={roles} />
      )}
    </div>
  )
}
