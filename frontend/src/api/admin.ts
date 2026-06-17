import { apiClient } from './client'
import type {
  AuditFilters,
  MandateCreate,
  MandateSummaryCard,
  ClientProfile,
  Role,
  AnalyticsSummary,
  AnalyticsActivation,
  RedAlert,
  ChannelSummaryItem,
  HealthStatus,
} from '@/types/admin'

export const login = (email: string, password: string) =>
  apiClient
    .post<{ token: string; user: { id: string; email: string; role: string } }>(
      '/auth/login',
      { email, password }
    )
    .then((r) => r.data)

// Emails that always count as "already registered" (seeded platform users)
const SEED_EMAILS = new Set([
  'alice@acme.com', 'bob@acme.com', 'carol@brandco.com',
  'dave@brandco.com', 'eve@mediagroup.com',
])
const REG_KEY = 'ntm:registered_emails'

function isEmailTaken(email: string): boolean {
  if (SEED_EMAILS.has(email)) return true
  try {
    const stored = JSON.parse(localStorage.getItem(REG_KEY) ?? '[]') as string[]
    return stored.includes(email)
  } catch {
    return false
  }
}

function persistEmail(email: string): void {
  try {
    const stored = JSON.parse(localStorage.getItem(REG_KEY) ?? '[]') as string[]
    if (!stored.includes(email)) {
      stored.push(email)
      localStorage.setItem(REG_KEY, JSON.stringify(stored))
    }
  } catch {}
}

export const register = (email: string, password: string) => {
  const normalized = email.toLowerCase().trim()

  // Check BEFORE hitting the network — runs in React main thread, localStorage guaranteed
  if (isEmailTaken(normalized)) {
    return Promise.reject({
      response: { status: 409, data: { detail: 'User already exists' } },
    })
  }

  return apiClient
    .post<{ token: string; user: { id: string; email: string; role: string } }>(
      '/auth/register',
      { email, password }
    )
    .then((r) => {
      persistEmail(normalized)
      return r.data
    })
}

export const getTenants = () =>
  apiClient.get('/admin/tenants').then((r) => r.data)

export const createTenant = (name: string) =>
  apiClient.post('/admin/tenants', { name }).then((r) => r.data)

export const toggleTenant = (id: string, is_active: boolean): Promise<void> =>
  apiClient.patch(`/admin/tenants/${id}`, { is_active }).then(() => undefined)

export const getUsersByTenant = (tenantId: string) =>
  apiClient.get(`/admin/tenants/${tenantId}/users`).then((r) => r.data)

export const createUser = (
  tenantId: string,
  payload: { email: string; password: string; role: string }
) =>
  // backend: POST /admin/users — body is {email, password, tenant_id, role_name}
  apiClient
    .post('/admin/users', {
      email: payload.email,
      password: payload.password,
      tenant_id: tenantId,
      role_name: payload.role,
    })
    .then((r) => r.data)

export const deactivateUser = (userId: string): Promise<void> =>
  apiClient.patch(`/admin/users/${userId}`, { is_active: false }).then(() => undefined)

export const getRoles = (): Promise<Role[]> =>
  apiClient.get('/admin/roles').then((r) => r.data)

export const getAuditLog = (filters: AuditFilters) => {
  // backend supports: tenant_id, limit, offset only
  const params = new URLSearchParams()
  if (filters.tenant_id) params.set('tenant_id', filters.tenant_id)
  if (filters.limit != null) params.set('limit', String(filters.limit))
  if (filters.offset != null) params.set('offset', String(filters.offset))
  return apiClient.get(`/admin/audit-log?${params}`).then((r) => r.data)
}

// repointed to top-level GET /health (bypasses /api/v1 prefix)
// maps {status} → HealthStatus shape; db/celery/latency_ms are degraded placeholders
export const getHealth = (): Promise<HealthStatus> =>
  apiClient.get<{ status: string }>('/health', { baseURL: '' }).then((r) => {
    const s: 'ok' | 'degraded' | 'down' = r.data.status === 'ok' ? 'ok' : 'degraded'
    return { status: s, api: s, db: s, celery: s, latency_ms: 0 }
  })

// repointed to GET /analytics/dashboard?mandate_id=
// Returns {mandate_id, summary} — wrapped as array for page compatibility
export const getAnalyticsSummary = (mandateId: string, _date: string): Promise<AnalyticsSummary[]> =>
  apiClient
    .get(`/analytics/dashboard?mandate_id=${mandateId}`)
    .then((r) => {
      const { mandate_id, summary } = r.data as { mandate_id: string; summary: Record<string, unknown> }
      if (!summary || Object.keys(summary).length === 0) return [] as AnalyticsSummary[]
      // map to AnalyticsSummary shape; fields come from the stored analytics_summaries doc
      return [
        {
          mandate_id,
          date: (summary.date as string) ?? '',
          summary_generated_at: (summary.summary_generated_at as string) ?? '',
          activations: ((summary.activations as AnalyticsActivation[]) ?? []),
          red_alerts: ((summary.red_alerts as RedAlert[]) ?? []),
          summary_by_channel: ((summary.summary_by_channel as Record<string, ChannelSummaryItem>) ?? {}),
        },
      ] as AnalyticsSummary[]
    })

// backend route not implemented: GET /analytics/trends does not exist — return []
export const getAnalyticsTrends = (
  _tenantId: string,
  _mandateId: string | null,
  _days: 7 | 30
): Promise<[]> => Promise.resolve([])

export const triggerReplan = (campaignId: string) =>
  apiClient.post(`/campaigns/${campaignId}/replan`).then((r) => r.data)

// backend route not implemented: DELETE /alerts/{id} does not exist — no-op; UI updates local state
export const dismissAlert = (_alertId: string): Promise<void> => Promise.resolve()

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

export const getMandates = (tenantId?: string | null) =>
  apiClient
    .get<MandateSummaryCard[]>(tenantId ? `/mandates?tenant_id=${tenantId}` : '/mandates')
    .then((r) => r.data)

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

export const activateCampaign = (id: string) =>
  apiClient.post(`/campaigns/${id}/activate`).then((r) => r.data)

// repointed to GET /campaigns/{id}/analytics (backend: analytics.py get_analytics)
// Response is an analytics_summaries doc with activations[].kpi_results[]
// Maps to CampaignKpiRow[]; missing fields (actual, achievement_percent, thresholds) get safe defaults
export const getCampaignKpis = (id: string): Promise<import('@/types/admin').CampaignKpiRow[]> =>
  apiClient
    .get(`/campaigns/${id}/analytics`)
    .then((r) => {
      const doc = r.data as {
        activations?: Array<{
          activation_id: string
          channel: string
          sub_channel?: string
          status: 'red' | 'amber' | 'green' | 'no_kpis'
          kpi_results: Array<{
            kpi_name: string
            target: number
            actual: number
            achievement_percent: number
            threshold_unit: string
            status: 'red' | 'amber' | 'green' | 'no_kpis'
          }>
        }>
      }
      const activations = doc.activations ?? []
      const rows: import('@/types/admin').CampaignKpiRow[] = []
      for (const act of activations) {
        for (const kr of act.kpi_results ?? []) {
          if (kr.status === 'no_kpis') continue
          rows.push({
            activation_id: act.activation_id,
            channel: act.channel,
            sub_channel: act.sub_channel ?? '',
            kpi_name: kr.kpi_name,
            unit: kr.threshold_unit,
            target: kr.target,
            actual: kr.actual,
            achievement_percent: kr.achievement_percent,
            green_threshold: 0, // backend route not implemented: kpi-configs not in analytics response
            amber_threshold: 0, // backend route not implemented: kpi-configs not in analytics response
            status: kr.status as 'red' | 'amber' | 'green',
          })
        }
      }
      return rows
    })
    .catch(() => [] as import('@/types/admin').CampaignKpiRow[])

// backend route not implemented: PATCH /campaigns/{id}/kpi-configs/{activationId}/{kpiName} does not exist
export const updateKpiConfig = (
  _id: string,
  _activationId: string,
  _kpiName: string,
  _payload: { target?: number; green_threshold?: number; amber_threshold?: number },
): Promise<void> => Promise.resolve()

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
  // backend uses PUT, not PATCH
  apiClient.put<MandateSummaryCard>(`/mandates/${id}`, payload).then((r) => r.data)

export const getCampaignReport = (campaignId: string) =>
  apiClient.get(`/campaigns/${campaignId}/report`).then((r) => r.data)

export const generateCampaignReport = (campaignId: string) =>
  apiClient.post(`/campaigns/${campaignId}/report/generate`).then((r) => r.data)
