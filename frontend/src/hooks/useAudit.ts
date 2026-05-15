import { useQuery } from '@tanstack/react-query'
import { getAuditLog } from '@/api/admin'
import type { AuditFilters } from '@/types/admin'

export function useAudit(filters: AuditFilters) {
  return useQuery({
    queryKey: ['audit', filters],
    queryFn: () => getAuditLog(filters),
  })
}
