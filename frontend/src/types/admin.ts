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

export interface Mandate {
  id: string
  name: string
  tenant_id: string
  budget: { total_budget: number; currency: string }
  geography: { regions: string[]; markets: string[]; country_list: string[] }
  created_at: string
  status?: MandateStatus
}

export type MandateObjective =
  | 'awareness'
  | 'consideration'
  | 'conversion'
  | 'loyalty'
  | 'engagement'

export type MandateStatus = 'draft' | 'pending_review' | 'confirmed' | 'rejected'

export interface ClientProfile {
  id: string
  org_name: string
  industry: string
  logo_url: string
  brand_guidelines_url: string
  competitors: string[]
  tenant_id: string
  created_at: string
}

export interface MandateCreate {
  name: string
  objective: MandateObjective
  region: string
  countries: string[]
  total_budget: number
  currency: string
  start_date: string
  end_date: string
  client_id: string
}

export interface MandateSummaryCard extends Mandate {
  objective: MandateObjective
  region: string
  countries: string[]
  start_date: string
  end_date: string
  status: MandateStatus
  client: ClientProfile
}

export interface CampaignConcept {
  id: string
  name: string
  tagline: string
  channels: string[]
  tone_board: string
  target_audience: string
  risk_flags: { legal: string | null; regulatory: string | null; sensitivity: string | null }
}

export interface Activation {
  id: string
  channel: string
  sub_channel: string
  budget: number
  currency: string
  audience: string
  kpis: { name: string; target: number; unit: string }[]
}

export interface BudgetAllocation {
  channel: string
  amount: number
  percentage: number
}

export interface BudgetProposal {
  total_budget: number
  currency: string
  allocations: BudgetAllocation[]
}

export type CampaignStatus =
  | 'pending'
  | 'concepts_ready'
  | 'confirmed'
  | 'planned'
  | 'budget_proposed'
  | 'approved'
  | 'creative_generating'
  | 'creative_ready'
  | 'live'

export interface Campaign {
  id: string
  mandate_id: string
  tenant_id: string
  status: CampaignStatus
  concepts: CampaignConcept[]
  selected_concept_id: string | null
  activation_plan: Activation[]
  budget_proposal: BudgetProposal | null
  creative_assets: CreativeAssets | null
  kpi_configs: KpiConfig[]
  created_at: string
  updated_at: string
}

export interface KpiConfig {
  activation_id: string
  kpi_name: string
  unit: string
  target: number
  green_threshold: number
  amber_threshold: number
}

export interface CampaignKpiRow {
  activation_id: string
  channel: string
  sub_channel: string
  kpi_name: string
  unit: string
  target: number
  actual: number
  achievement_percent: number
  green_threshold: number
  amber_threshold: number
  status: 'red' | 'amber' | 'green'
}

export type CopyAssetType =
  | 'social_caption'
  | 'headline'
  | 'body_copy'
  | 'print_ad'
  | 'email'
  | 'ooh_billboard'
  | 'influencer_brief'

export interface CopyVariant {
  variant: 'A' | 'B'
  content: string
  word_count: number
}

export interface CopyAsset {
  asset_type: CopyAssetType
  variants: CopyVariant[]
  approved: boolean | null
}

export interface ScriptAsset {
  id: string
  format: 'tvc_vo' | 'radio' | 'social_video'
  content: string
  duration_estimate: string
  approved: boolean | null
}

export interface ImageAsset {
  id: string
  format: 'square' | 'landscape' | 'portrait'
  url: string
  approved: boolean | null
}

export interface AudioAsset {
  id: string
  format: 'radio' | 'tvc_vo' | 'social_video'
  voice_style: 'warm' | 'authoritative' | 'youthful'
  url: string
  duration_seconds: number
  approved: boolean | null
}

export interface CreativeAssets {
  campaign_id: string
  copy: CopyAsset[]
  scripts: ScriptAsset[]
  images: ImageAsset[]
  audio: AudioAsset[]
}
