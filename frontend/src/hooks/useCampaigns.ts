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
  generateCreatives,
  approveCreativeAsset,
  regenerateAsset,
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

type AssetKind = 'copy' | 'scripts' | 'images' | 'audio'

export interface ApproveAssetPayload {
  assetKind: AssetKind
  assetId: string
  approved: boolean
}

export interface RegeneratePayload {
  assetKind: AssetKind
  assetId: string
}

export function useGenerateCreatives(campaignId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => generateCreatives(campaignId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['campaign', campaignId] }),
  })
}

export function useApproveCreativeAsset(campaignId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ assetKind, assetId, approved }: ApproveAssetPayload) =>
      approveCreativeAsset(campaignId, assetKind, assetId, approved),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['campaign', campaignId] }),
  })
}

export function useRegenerateAsset(campaignId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ assetKind, assetId }: RegeneratePayload) =>
      regenerateAsset(campaignId, assetKind, assetId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['campaign', campaignId] }),
  })
}
