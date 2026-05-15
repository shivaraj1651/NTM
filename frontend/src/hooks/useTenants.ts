import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getTenants, createTenant, toggleTenant } from '@/api/admin'

export function useTenants() {
  return useQuery({ queryKey: ['tenants'], queryFn: getTenants })
}

export function useCreateTenant() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (name: string) => createTenant(name),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tenants'] }),
  })
}

export function useToggleTenant() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      toggleTenant(id, is_active),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tenants'] }),
  })
}
