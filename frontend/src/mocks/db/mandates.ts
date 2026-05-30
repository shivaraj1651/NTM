import type { ClientProfile, MandateSummaryCard } from '@/types/admin'

// ── localStorage-persisted store ─────────────────────────────────────────────

function createPersistedStore<V>(
  storageKey: string,
  seed: Record<string, V>,
): Record<string, V> {
  let initial: Record<string, V>
  try {
    const raw = localStorage.getItem(storageKey)
    // Merge: seed provides defaults; stored data overrides (keeps user changes)
    initial = raw ? { ...seed, ...(JSON.parse(raw) as Record<string, V>) } : { ...seed }
  } catch {
    initial = { ...seed }
  }

  const persist = (target: Record<string, V>) => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(target))
    } catch {}
  }

  return new Proxy(initial, {
    set(target, prop, value) {
      const ok = Reflect.set(target, prop, value)
      persist(target)
      return ok
    },
    deleteProperty(target, prop) {
      const ok = Reflect.deleteProperty(target, prop)
      persist(target)
      return ok
    },
  })
}

// ── Seed data ────────────────────────────────────────────────────────────────

const SEED_CLIENT: ClientProfile = {
  id: 'cl-001',
  org_name: 'Acme Corp',
  industry: 'Technology',
  logo_url: 'https://placehold.co/100x100',
  brand_guidelines_url: 'https://example.com/brand.pdf',
  competitors: ['CompetitorA', 'CompetitorB'],
  tenant_id: 't1',
  created_at: '2026-03-01T00:00:00Z',
}

// ── Persisted exports ─────────────────────────────────────────────────────────

export const clientStore = createPersistedStore<ClientProfile>(
  'ntm:clients',
  { 'cl-001': SEED_CLIENT },
)

export const mandateStore = createPersistedStore<MandateSummaryCard>(
  'ntm:mandates',
  {
    'm-001': {
      id: 'm-001',
      name: 'Q3 Brand Awareness',
      tenant_id: 't1',
      total_budget: 50000,
      currency: 'USD',
      budget: { total_budget: 50000, currency: 'USD' },
      geography: { regions: ['Americas'], markets: ['US', 'CA'], country_list: ['USA', 'Canada'] },
      created_at: '2026-04-01T00:00:00Z',
      objective: 'awareness',
      region: 'Americas',
      countries: ['USA', 'Canada'],
      start_date: '2026-07-01',
      end_date: '2026-09-30',
      status: 'pending_review',
      client: SEED_CLIENT,
    },
    'm-002': {
      id: 'm-002',
      name: 'Product Launch APAC',
      tenant_id: 't1',
      total_budget: 120000,
      currency: 'USD',
      budget: { total_budget: 120000, currency: 'USD' },
      geography: { regions: ['APAC'], markets: ['SG', 'AU', 'JP'], country_list: ['Singapore', 'Australia', 'Japan'] },
      created_at: '2026-04-15T00:00:00Z',
      objective: 'conversion',
      region: 'APAC',
      countries: ['Singapore', 'Australia', 'Japan'],
      start_date: '2026-08-01',
      end_date: '2026-11-30',
      status: 'pending_review',
      client: SEED_CLIENT,
    },
  },
)
