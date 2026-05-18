import type { ClientProfile, MandateSummaryCard } from '@/types/admin'

export const clientStore: Record<string, ClientProfile> = {
  'cl-001': {
    id: 'cl-001',
    org_name: 'Acme Corp',
    industry: 'Technology',
    logo_url: 'https://placehold.co/100x100',
    brand_guidelines_url: 'https://example.com/brand.pdf',
    competitors: ['CompetitorA', 'CompetitorB'],
    tenant_id: 't1',
    created_at: '2026-03-01T00:00:00Z',
  },
}

export const mandateStore: Record<string, MandateSummaryCard> = {
  'm-001': {
    id: 'm-001',
    name: 'Q3 Brand Awareness',
    tenant_id: 't1',
    budget: { total_budget: 50000, currency: 'USD' },
    geography: { regions: ['Americas'], markets: ['US', 'CA'], country_list: ['USA', 'Canada'] },
    created_at: '2026-04-01T00:00:00Z',
    objective: 'awareness',
    region: 'Americas',
    countries: ['USA', 'Canada'],
    start_date: '2026-07-01',
    end_date: '2026-09-30',
    status: 'pending_review',
    client: clientStore['cl-001'],
  },
  'm-002': {
    id: 'm-002',
    name: 'Product Launch APAC',
    tenant_id: 't1',
    budget: { total_budget: 120000, currency: 'USD' },
    geography: { regions: ['APAC'], markets: ['SG', 'AU', 'JP'], country_list: ['Singapore', 'Australia', 'Japan'] },
    created_at: '2026-04-15T00:00:00Z',
    objective: 'conversion',
    region: 'APAC',
    countries: ['Singapore', 'Australia', 'Japan'],
    start_date: '2026-08-01',
    end_date: '2026-11-30',
    status: 'pending_review',
    client: clientStore['cl-001'],
  },
}
