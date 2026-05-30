import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'

// Aligned to backend GeneratedCreative.to_dict() (source of truth).
// MSW-only fields kept optional so existing tests and the CreativeStudio UI
// still compile against mock data.
export interface Creative {
  // ── Backend canonical fields ──────────────────────────────────────────────
  id: string
  campaign_id: string
  tenant_id?: string
  generation_id?: string
  /** Backend field name for the creative category (image/audio/copy/script…) */
  creative_type?: string
  /** Platform target (e.g. "instagram", "tvc") */
  platform?: string
  /** Free-form JSONB content blob returned by the backend */
  content?: Record<string, unknown> | null
  /** Backend approval state field */
  validation_status?: string
  refinement_attempts?: number
  created_at: string
  updated_at?: string | null
  // ── MSW-only / derived fields — kept optional for UI compatibility ─────────
  /** Derived from creative_type in MSW mocks; not a backend field */
  asset_type?: 'image' | 'audio' | 'video' | 'copy' | 'script'
  /** URL to the asset; lives inside content{} on the real backend */
  asset_url?: string | null
  /** Approval state alias used by MSW mocks (backend uses validation_status) */
  status?: 'ai_draft' | 'internal_review' | 'client_review' | 'approved' | 'revision_requested' | 'rejected'
  /** Display label from MSW mocks; backend stores this inside content{} */
  message_variant?: string
  /** Format descriptor from MSW mocks; backend stores this inside content{} */
  format_spec?: string
  /** Revision notes from MSW mocks; backend stores this inside content.feedback_log */
  notes?: string | null
}

export function useCreatives(campaignId?: string) {
  return useQuery<Creative[]>({
    queryKey: ['creatives', campaignId],
    queryFn: async () => {
      const url = campaignId
        ? `/creatives?campaign_id=${campaignId}`
        : '/creatives'
      const { data } = await apiClient.get(url)
      // Handler returns { creatives: [...], total: N } — extract the array
      return Array.isArray(data) ? data : (data.creatives ?? [])
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
      status: NonNullable<Creative['status']>
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
