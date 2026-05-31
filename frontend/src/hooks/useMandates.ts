import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getMandates,
  createClient,
  createMandate,
  getMandateSummaryCard,
  confirmMandate,
  updateMandate,
  createCampaign,
} from '@/api/admin'
import type { MandateCreate, MandateSummaryCard } from '@/types/admin'

export function useCreateClient() {
  return useMutation({
    mutationFn: (formData: FormData) => createClient(formData),
  })
}

export function useMandateList(tenantId: string | null) {
  return useQuery<MandateSummaryCard[]>({
    queryKey: ['mandates', tenantId],
    queryFn: () => getMandates(tenantId!),
    enabled: !!tenantId,
  })
}

export function useCreateMandate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: MandateCreate) => createMandate(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['mandates'] }),
  })
}

export function useMandateSummary(id: string) {
  return useQuery<MandateSummaryCard>({
    queryKey: ['mandate-summary', id],
    queryFn: () => getMandateSummaryCard(id),
    enabled: !!id,
    // The AGT-01 analysis runs asynchronously after create; poll until the
    // mandate leaves the pre-analysis states so the page reflects readiness.
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'draft' || status === 'analyzing' ? 3000 : false
    },
  })
}

export function useConfirmMandate(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      await confirmMandate(id)
      return createCampaign(id)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['mandates'] }),
  })
}

export function useUpdateMandate(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: Partial<MandateCreate>) => updateMandate(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['mandates'] })
      qc.invalidateQueries({ queryKey: ['mandate-summary', id] })
    },
  })
}
