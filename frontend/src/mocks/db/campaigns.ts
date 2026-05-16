import type {
  Campaign,
  Mandate,
  CampaignConcept,
  Activation,
  BudgetProposal,
  CreativeAssets,
  CopyAsset,
  ScriptAsset,
  ImageAsset,
  AudioAsset,
} from '@/types/admin'

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

export function generateCreativeAssets(campaignId: string): CreativeAssets {
  const copy: CopyAsset[] = [
    {
      asset_type: 'social_caption',
      variants: [
        { variant: 'A', content: 'Ready to transform your business? Our solutions help you scale faster than ever. #Innovation #Growth', word_count: 17 },
        { variant: 'B', content: 'Join 500+ companies already growing with us. Start your journey today. #BusinessGrowth', word_count: 14 },
      ],
      approved: null,
    },
    {
      asset_type: 'headline',
      variants: [
        { variant: 'A', content: 'Scale Smarter. Grow Faster. Win Bigger.', word_count: 6 },
        { variant: 'B', content: 'The Future of Business Starts Here.', word_count: 7 },
      ],
      approved: null,
    },
    {
      asset_type: 'body_copy',
      variants: [
        { variant: 'A', content: 'In today\'s competitive landscape, every decision counts. Our platform gives you the insights, tools, and support to outpace the competition. From real-time analytics to automated workflows, we\'ve built everything you need to grow with confidence.', word_count: 42 },
        { variant: 'B', content: 'What separates thriving businesses from struggling ones? Better data, faster decisions, and the right partner. That\'s what we deliver — proven results for companies like yours, backed by 10 years of expertise.', word_count: 35 },
      ],
      approved: null,
    },
    {
      asset_type: 'print_ad',
      variants: [
        { variant: 'A', content: 'HEADLINE: Your Growth, Amplified.\nBODY: We turn strategy into results. 500+ clients. 3× average ROI. Trusted by leaders in 40 countries.\nCTA: Get Started Today', word_count: 27 },
        { variant: 'B', content: 'HEADLINE: Don\'t Just Compete. Dominate.\nBODY: Market leaders choose us for precision targeting, unmatched reach, and measurable impact.\nCTA: See How We Do It', word_count: 24 },
      ],
      approved: null,
    },
    {
      asset_type: 'email',
      variants: [
        { variant: 'A', content: 'Subject: You\'re leaving money on the table\n\nHi [First Name],\n\nMost businesses only capture 30% of their growth potential. The other 70%? It\'s sitting in untapped channels and missed opportunities.\n\nWe fix that. Book a free 30-minute strategy session.\n\n[Book My Session]', word_count: 50 },
        { variant: 'B', content: 'Subject: Quick question about your Q3 targets\n\nHi [First Name],\n\nAre you on track to hit your Q3 goals? Our team has helped 200+ businesses close their growth gap — often within 60 days.\n\nNo obligation. Just clarity.\n\n[Schedule a Call]', word_count: 46 },
      ],
      approved: null,
    },
    {
      asset_type: 'ooh_billboard',
      variants: [
        { variant: 'A', content: 'GROW BOLD.\n[Logo] — example.com', word_count: 4 },
        { variant: 'B', content: 'RESULTS YOU CAN SEE.\n[Logo] — example.com', word_count: 5 },
      ],
      approved: null,
    },
    {
      asset_type: 'influencer_brief',
      variants: [
        { variant: 'A', content: 'CAMPAIGN BRIEF — Influencer Partnership\n\nObjective: Drive awareness among 25–40 professionals.\nKey Message: Our platform makes growing your business effortless.\nTone: Authentic, conversational — not salesy.\nMandatories: Mention the free trial. Tag @Brand. Use #GrowBold.\nDeliverables: 1× feed post + 3× Stories with link sticker.', word_count: 56 },
        { variant: 'B', content: 'INFLUENCER GUIDE — Brand Collaboration\n\nWhat we want: Show your real workflow using our tools.\nDon\'t: Read from a script or make it feel like an ad.\nDo: Be genuine. Share a specific win.\nMust-haves: Disclose partnership, tag @Brand, include swipe-up link.\nFormat: 60–90 second Reel or TikTok preferred.', word_count: 55 },
      ],
      approved: null,
    },
  ]

  const scripts: ScriptAsset[] = [
    {
      id: `${campaignId}-scr-1`,
      format: 'tvc_vo',
      content: '[OPEN ON: Busy city office, professionals at work]\n\nVO: Every day, thousands of decisions shape your business future.\n\n[CUT TO: Dashboard with rising metrics]\n\nVO: What if you had the clarity to make every one count?\n\n[CUT TO: Satisfied team celebrating]\n\nVO: [Brand]. Decisions made smarter.\n\n[SUPER: example.com]',
      duration_estimate: '30s',
      approved: null,
    },
    {
      id: `${campaignId}-scr-2`,
      format: 'radio',
      content: 'SFX: Upbeat music, fades under VO\n\nVO: Struggling to hit your growth targets? You\'re not alone — but you don\'t have to stay stuck. [Brand] helps businesses like yours unlock real, measurable growth. More leads. Better conversions. Higher ROI.\n\nVisit example.com and start your free trial. [Brand] — Grow Bolder.\n\nSFX: Music up and out',
      duration_estimate: '30s',
      approved: null,
    },
    {
      id: `${campaignId}-scr-3`,
      format: 'social_video',
      content: '[0:00–0:03] HOOK: Text overlay — "Still doing this manually?"\n[0:03–0:10] Pain point: spreadsheets, manual tracking\n[0:10–0:20] Product reveal: dashboard auto-updating in real time\n[0:20–0:25] Social proof: "Trusted by 500+ teams"\n[0:25–0:30] CTA: "Try free — link in bio"\n\nCaption: Work smarter, not harder. #ProductivityHack #GrowthMindset',
      duration_estimate: '30s',
      approved: null,
    },
  ]

  const images: ImageAsset[] = [
    { id: `${campaignId}-img-1`, format: 'square',    url: 'https://placehold.co/1024x1024/1a1a2e/ffffff?text=Square+Ad',    approved: null },
    { id: `${campaignId}-img-2`, format: 'landscape', url: 'https://placehold.co/1344x768/16213e/ffffff?text=Landscape+Ad', approved: null },
    { id: `${campaignId}-img-3`, format: 'portrait',  url: 'https://placehold.co/768x1344/0f3460/ffffff?text=Portrait+Ad',  approved: null },
  ]

  const audio: AudioAsset[] = [
    { id: `${campaignId}-aud-1`, format: 'radio',        voice_style: 'warm',          url: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3', duration_seconds: 30, approved: null },
    { id: `${campaignId}-aud-2`, format: 'tvc_vo',       voice_style: 'authoritative', url: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3', duration_seconds: 30, approved: null },
    { id: `${campaignId}-aud-3`, format: 'social_video', voice_style: 'youthful',      url: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3', duration_seconds: 30, approved: null },
  ]

  return { campaign_id: campaignId, copy, scripts, images, audio }
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
    creative_assets: null,
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
    creative_assets: null,
    created_at: '2026-05-08T11:00:00Z',
    updated_at: '2026-05-08T14:30:00Z',
  },
  'c-003': {
    id: 'c-003',
    mandate_id: 'm-002',
    tenant_id: 't1',
    status: 'creative_ready',
    concepts: baseConcepts,
    selected_concept_id: 'con-002',
    activation_plan: baseActivations,
    budget_proposal: baseBudgetProposal,
    creative_assets: generateCreativeAssets('c-003'),
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
