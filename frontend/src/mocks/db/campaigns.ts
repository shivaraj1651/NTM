import type { Campaign, Mandate, CampaignConcept, Activation, BudgetProposal } from '@/types/admin'

const baseConcepts: CampaignConcept[] = [
  {
    id: 'con-001',
    name: 'Bold Futures',
    tagline: 'Lead tomorrow, today.',
    channels: ['Google Ads', 'LinkedIn Ads'],
    tone_board: 'Confident, forward-looking, professional',
    target_audience: 'B2B decision-makers 35–55',
    risk_flags: { legal: null, regulatory: null, sensitivity: null },
  },
  {
    id: 'con-002',
    name: 'Human Connection',
    tagline: 'Where business meets trust.',
    channels: ['Meta Ads', 'Google Ads'],
    tone_board: 'Warm, authentic, community-driven',
    target_audience: 'SME owners 30–50',
    risk_flags: { legal: null, regulatory: 'Financial claims require disclaimer', sensitivity: null },
  },
  {
    id: 'con-003',
    name: 'Data-Driven Edge',
    tagline: 'Smarter decisions. Better results.',
    channels: ['LinkedIn Ads', 'Google Ads', 'Meta Ads'],
    tone_board: 'Analytical, authoritative, results-focused',
    target_audience: 'C-suite executives 40–60',
    risk_flags: { legal: 'Avoid superlative claims', regulatory: null, sensitivity: null },
  },
]

const baseActivations: Activation[] = [
  {
    id: 'act-001',
    channel: 'Google Ads',
    sub_channel: 'Search',
    budget: 12000,
    currency: 'USD',
    audience: 'In-market: B2B software',
    kpis: [
      { name: 'Clicks', target: 3000, unit: 'clicks' },
      { name: 'CTR', target: 3.5, unit: '%' },
      { name: 'Conversions', target: 150, unit: 'leads' },
    ],
  },
  {
    id: 'act-002',
    channel: 'LinkedIn Ads',
    sub_channel: 'Sponsored Content',
    budget: 18000,
    currency: 'USD',
    audience: 'Job title: CTO, CIO — Company size 200+',
    kpis: [
      { name: 'Impressions', target: 80000, unit: 'impressions' },
      { name: 'Engagement Rate', target: 1.8, unit: '%' },
      { name: 'Lead Gen Forms', target: 200, unit: 'leads' },
    ],
  },
  {
    id: 'act-003',
    channel: 'Meta Ads',
    sub_channel: 'Feed',
    budget: 8000,
    currency: 'USD',
    audience: 'Lookalike: existing customers 1%',
    kpis: [
      { name: 'Reach', target: 150000, unit: 'users' },
      { name: 'ROAS', target: 4.2, unit: 'x' },
    ],
  },
  {
    id: 'act-004',
    channel: 'Meta Ads',
    sub_channel: 'Stories',
    budget: 5000,
    currency: 'USD',
    audience: 'Retargeting: website visitors 30d',
    kpis: [
      { name: 'Video Views', target: 20000, unit: 'views' },
      { name: 'Click-Through', target: 2.1, unit: '%' },
    ],
  },
]

const baseBudgetProposal: BudgetProposal = {
  total_budget: 43000,
  currency: 'USD',
  allocations: [
    { channel: 'Google Ads', amount: 12000, percentage: 27.9 },
    { channel: 'LinkedIn Ads', amount: 18000, percentage: 41.9 },
    { channel: 'Meta Ads', amount: 13000, percentage: 30.2 },
  ],
}

const initialCampaigns: Record<string, Campaign> = {
  'c-001': {
    id: 'c-001',
    mandate_id: 'm-001',
    tenant_id: 't1',
    status: 'concepts_ready',
    concepts: baseConcepts,
    selected_concept_id: null,
    activation_plan: [],
    budget_proposal: null,
    created_at: '2026-05-10T09:00:00Z',
    updated_at: '2026-05-10T09:05:00Z',
  },
  'c-002': {
    id: 'c-002',
    mandate_id: 'm-001',
    tenant_id: 't1',
    status: 'planned',
    concepts: baseConcepts,
    selected_concept_id: 'con-001',
    activation_plan: baseActivations,
    budget_proposal: null,
    created_at: '2026-05-08T11:00:00Z',
    updated_at: '2026-05-08T14:30:00Z',
  },
  'c-003': {
    id: 'c-003',
    mandate_id: 'm-002',
    tenant_id: 't1',
    status: 'approved',
    concepts: baseConcepts,
    selected_concept_id: 'con-002',
    activation_plan: baseActivations,
    budget_proposal: baseBudgetProposal,
    created_at: '2026-05-05T10:00:00Z',
    updated_at: '2026-05-12T16:00:00Z',
  },
}

export const campaignStore: Record<string, Campaign> = { ...initialCampaigns }

export const mandates: Mandate[] = [
  {
    id: 'm-001',
    name: 'Q3 Brand Awareness',
    tenant_id: 't1',
    budget: { total_budget: 50000, currency: 'USD' },
    geography: { regions: ['North America'], markets: ['US', 'CA'], country_list: ['United States', 'Canada'] },
    created_at: '2026-04-01T00:00:00Z',
  },
  {
    id: 'm-002',
    name: 'Product Launch APAC',
    tenant_id: 't1',
    budget: { total_budget: 120000, currency: 'USD' },
    geography: { regions: ['Asia Pacific'], markets: ['SG', 'AU', 'JP'], country_list: ['Singapore', 'Australia', 'Japan'] },
    created_at: '2026-04-15T00:00:00Z',
  },
]

export function generateConcepts(mandateId: string): CampaignConcept[] {
  return [
    {
      id: `${mandateId}-con-a`,
      name: 'Market Pioneer',
      tagline: 'First to market, first in mind.',
      channels: ['Google Ads', 'LinkedIn Ads'],
      tone_board: 'Bold, innovative, pioneering',
      target_audience: 'Industry leaders and early adopters',
      risk_flags: { legal: null, regulatory: null, sensitivity: null },
    },
    {
      id: `${mandateId}-con-b`,
      name: 'Trust Builder',
      tagline: 'Reliability you can count on.',
      channels: ['Meta Ads'],
      tone_board: 'Warm, dependable, community-focused',
      target_audience: 'Mainstream buyers seeking reassurance',
      risk_flags: { legal: null, regulatory: null, sensitivity: null },
    },
    {
      id: `${mandateId}-con-c`,
      name: 'ROI Focus',
      tagline: 'Every dollar working harder.',
      channels: ['Google Ads', 'Meta Ads', 'LinkedIn Ads'],
      tone_board: 'Analytical, results-driven, precise',
      target_audience: 'Finance-conscious decision-makers',
      risk_flags: { legal: 'Avoid ROI guarantees', regulatory: null, sensitivity: null },
    },
  ]
}

export function generateActivationPlan(mandateId: string): Activation[] {
  const mandate = mandates.find((m) => m.id === mandateId)
  const total = mandate?.budget.total_budget ?? 50000
  const currency = mandate?.budget.currency ?? 'USD'
  return [
    {
      id: 'act-gen-1',
      channel: 'Google Ads',
      sub_channel: 'Search',
      budget: Math.round(total * 0.3),
      currency,
      audience: 'In-market buyers',
      kpis: [{ name: 'Clicks', target: 2000, unit: 'clicks' }, { name: 'Conversions', target: 100, unit: 'leads' }],
    },
    {
      id: 'act-gen-2',
      channel: 'Meta Ads',
      sub_channel: 'Feed',
      budget: Math.round(total * 0.35),
      currency,
      audience: 'Lookalike: existing customers',
      kpis: [{ name: 'Reach', target: 100000, unit: 'users' }, { name: 'ROAS', target: 3.5, unit: 'x' }],
    },
    {
      id: 'act-gen-3',
      channel: 'LinkedIn Ads',
      sub_channel: 'Sponsored Content',
      budget: Math.round(total * 0.35),
      currency,
      audience: 'Decision-makers at target companies',
      kpis: [{ name: 'Impressions', target: 60000, unit: 'impressions' }, { name: 'Lead Gen Forms', target: 150, unit: 'leads' }],
    },
  ]
}

export function generateBudgetProposal(activations: Activation[]): BudgetProposal {
  const total = activations.reduce((sum, a) => sum + a.budget, 0)
  const currency = activations[0]?.currency ?? 'USD'
  const byChannel: Record<string, number> = {}
  for (const a of activations) {
    byChannel[a.channel] = (byChannel[a.channel] ?? 0) + a.budget
  }
  const allocations = Object.entries(byChannel).map(([channel, amount]) => ({
    channel,
    amount,
    percentage: Math.round((amount / total) * 1000) / 10,
  }))
  return { total_budget: total, currency, allocations }
}
