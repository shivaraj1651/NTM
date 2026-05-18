import { apiClient } from './client'
import type { AuditFilters, MandateCreate, MandateSummaryCard, ClientProfile } from '@/types/admin'

export const login = (email: string, password: string) =>
  apiClient
    .post<{ token: string; user: { id: string; email: string; role: string } }>(
      '/auth/login',
      { email, password }
    )
    .then((r) => r.data)

export const getTenants = () =>
  apiClient.get('/admin/tenants').then((r) => r.data)

export const createTenant = (name: string) =>
  apiClient.post('/admin/tenants', { name }).then((r) => r.data)

export const toggleTenant = (id: string, is_active: boolean) =>
  apiClient.patch(`/admin/tenants/${id}`, { is_active }).then((r) => r.data)

export const getUsersByTenant = (tenantId: string) =>
  apiClient.get(`/admin/tenants/${tenantId}/users`).then((r) => r.data)

export const createUser = (
  tenantId: string,
  payload: { email: string; password: string; role: string }
) =>
  apiClient.post(`/admin/tenants/${tenantId}/users`, payload).then((r) => r.data)

export const deactivateUser = (userId: string) =>
  apiClient.patch(`/admin/users/${userId}`, { is_active: false }).then((r) => r.data)

export const getRoles = () =>
  apiClient.get('/admin/roles').then((r) => r.data)

export const getAuditLog = (filters: AuditFilters) => {
  const params = new URLSearchParams()
  if (filters.entity_type) params.set('entity_type', filters.entity_type)
  if (filters.actor) params.set('actor', filters.actor)
  if (filters.from) params.set('from', filters.from)
  if (filters.to) params.set('to', filters.to)
  return apiClient.get(`/admin/audit?${params}`).then((r) => r.data)
}

export const getHealth = () =>
  apiClient.get('/admin/health').then((r) => r.data)

export const getAnalyticsSummary = (tenantId: string, date: string) =>
  apiClient
    .get(`/analytics/summary?tenant_id=${tenantId}&date=${date}`)
    .then((r) => r.data)

export const getAnalyticsTrends = (
  tenantId: string,
  mandateId: string | null,
  days: 7 | 30
) => {
  const params = new URLSearchParams({ tenant_id: tenantId, days: String(days) })
  if (mandateId) params.set('mandate_id', mandateId)
  return apiClient.get(`/analytics/trends?${params}`).then((r) => r.data)
}

export const triggerReplan = (campaignId: string) =>
  apiClient.post(`/campaigns/${campaignId}/replan`).then((r) => r.data)

export const dismissAlert = (alertId: string) =>
  apiClient.delete(`/alerts/${alertId}`).then((r) => r.data)

export const getCampaigns = (tenantId: string) =>
  apiClient.get(`/campaigns?tenant_id=${tenantId}`).then((r) => r.data)

export const getCampaign = (id: string) =>
  apiClient.get(`/campaigns/${id}`).then((r) => r.data)

export const createCampaign = (mandateId: string) =>
  apiClient.post('/campaigns', { mandate_id: mandateId }).then((r) => r.data)

export const confirmConcept = (id: string, selectedConceptId: string) =>
  apiClient
    .post(`/campaigns/${id}/confirm`, { selected_concept_id: selectedConceptId })
    .then((r) => r.data)

export const getActivationPlan = (id: string) =>
  apiClient.get(`/campaigns/${id}/activation-plan`).then((r) => r.data)

export const approveBudget = (id: string) =>
  apiClient.post(`/campaigns/${id}/approve-budget`).then((r) => r.data)

export const confirmBudget = (id: string) =>
  apiClient.post(`/campaigns/${id}/confirm-budget`).then((r) => r.data)

export const getMandates = (tenantId: string) =>
  apiClient.get<MandateSummaryCard[]>(`/mandates?tenant_id=${tenantId}`).then((r) => r.data)

export const generateCreatives = (id: string) =>
  apiClient.post(`/campaigns/${id}/generate-creatives`).then((r) => r.data)

export const approveCreativeAsset = (
  id: string,
  assetKind: string,
  assetId: string,
  approved: boolean,
) =>
  apiClient
    .patch(`/campaigns/${id}/creatives/${assetKind}/${assetId}`, { approved })
    .then((r) => r.data)

export const regenerateAsset = (id: string, assetKind: string, assetId: string) =>
  apiClient
    .post(`/campaigns/${id}/creatives/${assetKind}/${assetId}/regenerate`)
    .then((r) => r.data)

export const goLive = (id: string) =>
  apiClient.post(`/campaigns/${id}/go-live`).then((r) => r.data)

export const getCampaignKpis = (id: string) =>
  apiClient.get(`/campaigns/${id}/kpis`).then((r) => r.data)

export const updateKpiConfig = (
  id: string,
  activationId: string,
  kpiName: string,
  payload: { target?: number; green_threshold?: number; amber_threshold?: number },
) =>
  apiClient
    .patch(`/campaigns/${id}/kpi-configs/${activationId}/${kpiName}`, payload)
    .then((r) => r.data)

export const createClient = (formData: FormData) =>
  apiClient
    .post<ClientProfile>('/clients', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((r) => r.data)

export const createMandate = (payload: MandateCreate) =>
  apiClient.post<MandateSummaryCard>('/mandates', payload).then((r) => r.data)

export const getMandate = (id: string) =>
  apiClient.get<MandateSummaryCard>(`/mandates/${id}`).then((r) => r.data)

export const getMandateSummaryCard = (id: string) =>
  apiClient.get<MandateSummaryCard>(`/mandates/${id}/summary-card`).then((r) => r.data)

export const confirmMandate = (id: string) =>
  apiClient.post<MandateSummaryCard>(`/mandates/${id}/confirm`).then((r) => r.data)

export const updateMandate = (id: string, payload: Partial<MandateCreate>) =>
  apiClient.patch<MandateSummaryCard>(`/mandates/${id}`, payload).then((r) => r.data)
