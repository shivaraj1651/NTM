import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getCampaignReport, generateCampaignReport } from '@/api/admin'

export interface CampaignReport {
  mandate_id: string
  tenant_id: string
  report_type: string
  period_start: string
  period_end: string
  report_json: Record<string, unknown>
}

export function useCampaignReport(campaignId: string | null) {
  return useQuery<CampaignReport>({
    queryKey: ['campaign-report', campaignId],
    queryFn: () => getCampaignReport(campaignId!),
    enabled: !!campaignId,
    retry: (count, err: any) => err?.response?.status === 404 ? false : count < 2,
  })
}

export function useGenerateCampaignReport(campaignId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => generateCampaignReport(campaignId),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['campaign-report', campaignId] }),
  })
}
