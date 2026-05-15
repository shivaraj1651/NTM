import { apiClient } from './client'
import type { AuditFilters } from '@/types/admin'

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
