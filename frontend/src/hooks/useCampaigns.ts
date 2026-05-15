import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getCampaigns,
  getCampaign,
  createCampaign,
  confirmConcept,
  getActivationPlan,
  approveBudget,
  confirmBudget,
  getMandates,
} from '@/api/admin'
import type { Campaign, Mandate } from '@/types/admin'

export function useCampaigns(tenantId: string | null) {
  return useQuery<Campaign[]>({
    queryKey: ['campaigns', tenantId],
    queryFn: () => getCampaigns(tenantId!),
    enabled: !!tenantId,
  })
}

export function useCampaign(campaignId: string) {
  return useQuery<Campaign>({
    queryKey: ['campaign', campaignId],
    queryFn: () => getCampaign(campaignId),
    enabled: !!campaignId,
  })
}

export function useCreateCampaign() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (mandateId: string) => createCampaign(mandateId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['campaigns'] }),
  })
}

export function useConfirmConcept(campaignId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (selectedConceptId: string) => confirmConcept(campaignId, selectedConceptId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['campaign', campaignId] }),
  })
}

export function useActivationPlan(campaignId: string, enabled: boolean) {
  return useQuery<Campaign>({
    queryKey: ['campaign', campaignId, 'activation-plan'],
    queryFn: () => getActivationPlan(campaignId),
    enabled,
  })
}

export function useApproveBudget(campaignId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => approveBudget(campaignId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['campaign', campaignId] }),
  })
}

export function useConfirmBudget(campaignId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => confirmBudget(campaignId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['campaign', campaignId] }),
  })
}

export function useMandates(tenantId: string | null) {
  return useQuery<Mandate[]>({
    queryKey: ['mandates', tenantId],
    queryFn: () => getMandates(tenantId!),
    enabled: !!tenantId,
  })
}
