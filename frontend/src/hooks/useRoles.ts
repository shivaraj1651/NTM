import { useQuery } from '@tanstack/react-query'
import { getRoles } from '@/api/admin'

export function useRoles() {
  return useQuery({
    queryKey: ['roles'],
    queryFn: getRoles,
    staleTime: Infinity,
  })
}
