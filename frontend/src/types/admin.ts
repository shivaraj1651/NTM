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
