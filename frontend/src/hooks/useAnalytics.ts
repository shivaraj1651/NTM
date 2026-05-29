import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getAnalyticsSummary,
  getAnalyticsTrends,
  triggerReplan,
  dismissAlert,
} from '@/api/admin'
import type { AnalyticsSummary, TrendPoint } from '@/types/admin'

// tenantId param kept for API compatibility but backend uses mandate_id.
// Pass mandate_id as the first arg (was tenantId); date is unused by the real endpoint.
export function useAnalyticsSummary(mandateId: string | null, date: string) {
  return useQuery<AnalyticsSummary[]>({
    queryKey: ['analytics-summary', mandateId, date],
    queryFn: () => getAnalyticsSummary(mandateId!, date),
    enabled: !!mandateId,
    staleTime: 5 * 60 * 1000,
  })
}

// backend route not implemented: GET /analytics/trends — returns [] always
export function useAnalyticsTrends(
  tenantId: string | null,
  mandateId: string | null,
  days: 7 | 30
) {
  return useQuery<TrendPoint[]>({
    queryKey: ['analytics-trends', tenantId, mandateId, days],
    queryFn: () => getAnalyticsTrends(tenantId ?? '', mandateId, days),
    enabled: !!tenantId,
  })
}

export function useTriggerReplan() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (campaignId: string) => triggerReplan(campaignId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['analytics-summary'] }),
  })
}

export function useDismissAlert() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (alertId: string) => dismissAlert(alertId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['analytics-summary'] }),
  })
}
