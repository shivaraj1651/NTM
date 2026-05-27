import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'

export interface Creative {
  id: string
  campaign_id: string
  asset_type: 'image' | 'audio' | 'video' | 'copy' | 'script'
  asset_url: string | null
  status: 'ai_draft' | 'internal_review' | 'client_review' | 'approved' | 'revision_requested' | 'rejected'
  message_variant: string
  format_spec: string
  notes: string | null
  created_at: string
}

export function useCreatives(campaignId?: string) {
  return useQuery<Creative[]>({
    queryKey: ['creatives', campaignId],
    queryFn: async () => {
      const url = campaignId
        ? `/creatives?campaign_id=${campaignId}`
        : '/creatives'
      const { data } = await apiClient.get(url)
      return data
    },
    enabled: true,
  })
}

export function useCreative(assetId: string) {
  return useQuery<Creative>({
    queryKey: ['creative', assetId],
    queryFn: async () => {
      const { data } = await apiClient.get(`/creatives/${assetId}`)
      return data
    },
    enabled: !!assetId,
  })
}

export function useUpdateCreativeStatus() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({
      id,
      status,
      notes,
    }: {
      id: string
      status: Creative['status']
      notes?: string
    }) => {
      const { data } = await apiClient.patch(`/creatives/${id}/status`, { status, notes })
      return data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['creatives'] })
      qc.invalidateQueries({ queryKey: ['creative'] })
    },
  })
}
