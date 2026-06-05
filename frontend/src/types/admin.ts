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

// Aligned to backend AuditLogResponse schema
export interface AuditEntry {
  id: string
  created_at: string
  actor_id: string
  action: string
  entity_type: string
  entity_id: string
  tenant_id: string
  notes: string | null
  status_before: string | null
  status_after: string | null
}

// backend GET /health returns {status: "ok"} only
// api/db/celery/latency_ms are degraded to derived/placeholder values
export interface HealthStatus {
  status: 'ok' | 'degraded' | 'down'
  api: 'ok' | 'degraded' | 'down'
  db: 'ok' | 'degraded' | 'down'
  celery: 'ok' | 'degraded' | 'down'
  latency_ms: number
}

// backend GET /admin/audit-log supports: tenant_id, limit, offset only
export interface AuditFilters {
  tenant_id?: string
  limit?: number
  offset?: number
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

export type MandateObjective =
  | 'awareness'
  | 'consideration'
  | 'conversion'
  | 'loyalty'
  | 'engagement'

export type MandateStatus =
  | 'draft'
  | 'analyzing'
  | 'analyzed'
  | 'pending_review'
  | 'confirmed'
  | 'rejected'

// Aligned to backend MandateResponse (flat fields).
// `budget` and `geography` kept optional for MSW mock compatibility.
export interface Mandate {
  id: string
  name: string
  tenant_id: string
  client_id?: string
  // flat fields from backend MandateResponse
  total_budget?: number
  currency?: string
  objective?: MandateObjective
  region?: string
  countries?: string[]
  cities?: string[]
  competitors?: string[]
  start_date?: string
  end_date?: string
  description?: string | null
  status?: MandateStatus
  updated_at?: string | null
  created_at: string
  // nested shape kept optional for MSW mock compatibility
  budget?: { total_budget: number; currency: string }
  geography?: { regions: string[]; markets: string[]; country_list: string[] }
}

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
  cities?: string[]
  total_budget: number
  currency: string
  start_date: string
  end_date: string
  client_id: string
}

// MandateSummaryCard — used by mandate list/summary pages.
// Backend returns flat MandateResponse (no nested budget/geography/client).
// MSW mocks include client; mark it optional so both sources work.
export interface MandateSummaryCard extends Mandate {
  // override optionals to required for the summary card context
  objective: MandateObjective
  region: string
  countries: string[]
  cities?: string[]
  start_date: string
  end_date: string
  total_budget: number
  currency: string
  status: MandateStatus
  // client is NOT returned by the backend (only client_id); optional for MSW compat
  client?: ClientProfile
}

export interface CampaignConcept {
  id: string
  name: string
  tagline: string
  // Simple shape (MSW / legacy)
  channels?: string[]
  target_audience?: string
  // tone_board is a string in the simple shape, an object in the backend AGT-03 shape
  tone_board?: string | { adjectives?: string[]; visual_direction?: string }
  // Rich backend (AGT-03) shape
  channel_mix?: { channel: string; rationale?: string; competitor_gap?: string }[]
  audience_segmentation?: { primary?: string; secondary?: string; tertiary?: string }
  risk_flags: { legal: string | null; regulatory: string | null; sensitivity: string | null }
}

export interface Activation {
  id: string
  // Real backend (AGT-04) fields
  channel_enum?: string
  sub_channel: string
  format?: string
  geography?: string
  placement?: string
  phase?: string
  audience_segment?: string
  estimated_reach?: number
  estimated_cpm?: number
  cost_estimated?: number
  // Legacy MSW shape (kept optional for test compat)
  channel?: string
  budget?: number
  currency?: string
  audience?: string
  kpis?: { name: string; target: number; unit: string }[]
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
  executive_summary?: string
}

export type CampaignStatus =
  | 'pending'
  | 'concepts_ready'
  | 'confirmed'
  | 'planned'
  | 'budget_pending'
  | 'budget_proposed'
  | 'approved'
  | 'creative_generating'
  | 'creative_ready'
  | 'live'

export type CreativeStage = 'internal_review' | 'client_review' | 'locked'
export type ReviewAction = 'approve' | 'request_change' | 'reject'

// Aligned to backend CampaignResponse.
// activation_plan is list | null on the backend; updated_at can be null.
export interface PlatformActivationResult {
  status: 'queued' | 'live' | 'test_live' | 'failed'
  campaign_id: string | null
  ad_id: string | null
  ad_set_id?: string | null
  test_mode?: boolean
  error: string | null
  updated_at?: string | null
}

export interface Campaign {
  id: string
  mandate_id: string
  tenant_id: string
  status: CampaignStatus
  concepts: CampaignConcept[]
  selected_concept_id: string | null
  activation_plan: Activation[] | null
  budget_proposal: BudgetProposal | null
  creative_assets: CreativeAssets | null
  kpi_configs: KpiConfig[]
  /** Populated by Celery activation tasks — one entry per platform (google_ads, meta_ads) */
  activation_results?: Record<string, PlatformActivationResult> | null
  created_at: string | null
  updated_at: string | null
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
  | 'linkedin_post'

export interface CopyVariant {
  // Real backend (AGT-07) shape
  variant_id?: string
  content: string | { text?: string; subject?: string; body?: string; [key: string]: unknown }
  word_count: number
  rationale?: string
  // Legacy MSW shape
  variant?: 'A' | 'B'
}

export interface CopyAsset {
  asset_type: CopyAssetType
  variants: CopyVariant[]
  approved: boolean | null
  revision_count: number
}

export interface ScriptAsset {
  // Real backend (AGT-08) shape
  duration_label?: string
  total_duration_seconds?: number
  scenes?: { scene_number: number; description: string; action?: string; dialogue?: string }[]
  directors_note?: string
  talent_suggestions?: string[]
  location_suggestions?: string[]
  wardrobe_notes?: string
  music_direction?: string
  // Legacy MSW shape
  id?: string
  format?: 'tvc_vo' | 'radio' | 'social_video'
  content?: string
  duration_estimate?: string
  approved: boolean | null
  revision_count: number
}

export interface ImageAsset {
  id: string
  format: 'square' | 'landscape' | 'portrait' | 'ooh_billboard' | 'newspaper_insert' | 'linkedin_post'
  url: string
  approved: boolean | null
  revision_count: number
}

export interface AudioAsset {
  id: string
  format: 'radio' | 'tvc_vo' | 'social_video'
  voice_style: 'warm' | 'authoritative' | 'youthful'
  url: string
  duration_seconds: number
  approved: boolean | null
  revision_count: number
}

export interface VideoAsset {
  id: string
  format: string
  url: string
  job_id?: string
  model_used?: string
  duration_seconds?: number
  status?: string
  approved: boolean | null
  revision_count: number
}

export interface CreativeAssets {
  campaign_id: string
  stage: CreativeStage
  copy: CopyAsset[]
  scripts: ScriptAsset[]
  images: ImageAsset[]
  audio: AudioAsset[]
  video?: VideoAsset[]
}
