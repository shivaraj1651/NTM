import { useQuery, useMutation } from '@tanstack/react-query'
import {
  getAnalyticsSummary,
  getAnalyticsTrends,
  triggerReplan,
  dismissAlert,
} from '@/api/admin'
import type { AnalyticsSummary, TrendPoint } from '@/types/admin'

export function useAnalyticsSummary(tenantId: string | null, date: string) {
  return useQuery<AnalyticsSummary[]>({
    queryKey: ['analytics-summary', tenantId, date],
    queryFn: () => getAnalyticsSummary(tenantId!, date),
    enabled: !!tenantId,
    staleTime: 5 * 60 * 1000,
  })
}

export function useAnalyticsTrends(
  tenantId: string | null,
  mandateId: string | null,
  days: 7 | 30
) {
  return useQuery<TrendPoint[]>({
    queryKey: ['analytics-trends', tenantId, mandateId, days],
    queryFn: () => getAnalyticsTrends(tenantId!, mandateId, days),
    enabled: !!tenantId,
  })
}

export function useTriggerReplan() {
  return useMutation({
    mutationFn: (campaignId: string) => triggerReplan(campaignId),
  })
}

export function useDismissAlert() {
  return useMutation({
    mutationFn: (alertId: string) => dismissAlert(alertId),
  })
}
