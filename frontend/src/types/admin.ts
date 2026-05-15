export interface Tenant {
  id: string
  name: string
  is_active: boolean
  created_at: string
}

export interface User {
  id: string
  email: string
  role: string
  is_active: boolean
  tenant_id: string
  created_at: string
}

export interface Role {
  id: string
  name: string
  permissions: string[]
  user_count: number
}

export interface AuditEntry {
  id: string
  timestamp: string
  actor: string
  action: string
  entity_type: string
  entity_id: string
  detail: string
}

export interface HealthStatus {
  api: 'ok' | 'degraded' | 'down'
  db: 'ok' | 'degraded' | 'down'
  celery: 'ok' | 'degraded' | 'down'
  latency_ms: number
}

export interface AuditFilters {
  entity_type?: string
  actor?: string
  from?: string
  to?: string
}

export const ROLES = [
  'platform_admin',
  'tenant_admin',
  'brand_manager',
  'cmo',
  'creative_lead',
  'campaign_manager',
  'viewer',
] as const

export type RoleName = (typeof ROLES)[number]

export interface KpiResult {
  kpi_name: string
  target: number
  actual: number
  achievement_percent: number
  threshold_unit: string
  status: 'red' | 'amber' | 'green' | 'no_kpis'
}

export interface ActivationMetrics {
  impressions: number
  clicks: number
  conversions: number
  spend: number
}

export interface AnalyticsActivation {
  activation_id: string
  campaign_id: string
  channel: string
  sub_channel?: string
  status: 'red' | 'amber' | 'green' | 'no_kpis'
  kpi_results: KpiResult[]
  metrics: ActivationMetrics
}

export interface RedAlert {
  activation_id: string
  campaign_id: string
  channel: string
  failed_kpi: string
  severity: 'red'
}

export interface ChannelSummaryItem {
  total: number
  red: number
  amber: number
  green: number
}

export interface AnalyticsSummary {
  mandate_id: string
  date: string
  summary_generated_at: string
  activations: AnalyticsActivation[]
  red_alerts: RedAlert[]
  summary_by_channel: Record<string, ChannelSummaryItem>
}

export interface TrendPoint {
  date: string
  spend: number
  impressions: number
}
