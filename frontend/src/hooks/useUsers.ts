import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getUsersByTenant, createUser, deactivateUser } from '@/api/admin'

export function useUsers(tenantId: string | null) {
  return useQuery({
    queryKey: ['users', tenantId],
    queryFn: () => getUsersByTenant(tenantId!),
    enabled: !!tenantId,
  })
}

export function useCreateUser(tenantId: string | null) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: { email: string; password: string; role: string }) =>
      createUser(tenantId!, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users', tenantId] }),
  })
}

export function useDeactivateUser(tenantId?: string | null) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (userId: string) => deactivateUser(userId),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: tenantId ? ['users', tenantId] : ['users'],
      }),
  })
}
