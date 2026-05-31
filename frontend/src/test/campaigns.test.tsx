import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from './setup'
import { CampaignsPage } from '@/pages/Admin/Campaigns/CampaignsPage'
import { CampaignDetailPage } from '@/pages/Admin/Campaigns/CampaignDetailPage'
import { ConceptsPage } from '@/pages/Admin/Campaigns/ConceptsPage'
import { PlanPage } from '@/pages/Admin/Campaigns/PlanPage'
import { BudgetPage } from '@/pages/Admin/Campaigns/BudgetPage'
import { CreativesPage } from '@/pages/Admin/Campaigns/CreativesPage'
import { GoLivePage } from '@/pages/Admin/Campaigns/GoLivePage'
import { KpisPage } from '@/pages/Admin/Campaigns/KpisPage'
import { renderWithProviders, renderCampaignPage, CAMPAIGN_MANAGER_USER } from './utils'

// ── CampaignsPage ────────────────────────────────────────────────────────────

describe('CampaignsPage', () => {
  it('renders without crashing', () => {
    renderWithProviders(<CampaignsPage />, {
      route: '/admin/campaigns',
      path: '/admin/campaigns',
      user: CAMPAIGN_MANAGER_USER,
    })
    expect(document.body).toBeInTheDocument()
  })

  it('shows page heading', () => {
    renderWithProviders(<CampaignsPage />, {
      route: '/admin/campaigns',
      path: '/admin/campaigns',
      user: CAMPAIGN_MANAGER_USER,
    })
    expect(screen.getByText(/Campaigns/i)).toBeInTheDocument()
  })

  it('loads all 4 seeded campaigns for tenant t1', async () => {
    renderWithProviders(<CampaignsPage />, {
      route: '/admin/campaigns',
      path: '/admin/campaigns',
      user: CAMPAIGN_MANAGER_USER,
    })
    await waitFor(() => {
      expect(screen.getByText('c-001')).toBeInTheDocument()
      expect(screen.getByText('c-002')).toBeInTheDocument()
      expect(screen.getByText('c-003')).toBeInTheDocument()
      expect(screen.getByText('c-004')).toBeInTheDocument()
    })
  })

  it('shows New Campaign button', async () => {
    renderWithProviders(<CampaignsPage />, {
      route: '/admin/campaigns',
      path: '/admin/campaigns',
      user: CAMPAIGN_MANAGER_USER,
    })
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /new campaign/i })).toBeInTheDocument()
    )
  })
})

// ── CampaignDetailPage ───────────────────────────────────────────────────────

describe('CampaignDetailPage', () => {
  it('renders without crashing', () => {
    renderWithProviders(<CampaignDetailPage />, {
      route: '/admin/campaigns/c-001',
      path: '/admin/campaigns/:id',
    })
    expect(document.body).toBeInTheDocument()
  })

  it('renders all 9 stepper steps', async () => {
    renderWithProviders(<CampaignDetailPage />, {
      route: '/admin/campaigns/c-001',
      path: '/admin/campaigns/:id',
    })
    await waitFor(() => {
      for (const step of [
        'Create', 'Concepts', 'Confirmed', 'Plan',
        'Budget', 'Approved', 'Creatives', 'Go Live', 'KPIs',
      ]) {
        expect(screen.getByText(step)).toBeInTheDocument()
      }
    })
  })
})

// ── ConceptsPage (c-001 — concepts_ready) ────────────────────────────────────

describe('ConceptsPage', () => {
  it('renders without crashing', () => {
    renderCampaignPage(<ConceptsPage />, 'c-001')
    expect(document.body).toBeInTheDocument()
  })

  it('loads all 3 concept names from MSW', async () => {
    renderCampaignPage(<ConceptsPage />, 'c-001')
    await waitFor(() => {
      expect(screen.getByText('Bold Futures')).toBeInTheDocument()
      expect(screen.getByText('Human Connection')).toBeInTheDocument()
      expect(screen.getByText('Data-Driven Edge')).toBeInTheDocument()
    })
  })

  it('shows Confirm Selection button', async () => {
    renderCampaignPage(<ConceptsPage />, 'c-001')
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /confirm selection/i })).toBeInTheDocument()
    )
  })

  it('shows a generating state while concepts are pending', async () => {
    server.use(http.get('/api/v1/campaigns/:id', () =>
      HttpResponse.json({ id: 'c-gen', mandate_id: 'm', tenant_id: 't1', status: 'pending',
        concepts: [], selected_concept_id: null, activation_plan: null, budget_proposal: null,
        creative_assets: null, kpi_configs: [], created_at: '2026-05-31T00:00:00Z', updated_at: '2026-05-31T00:00:00Z' })))
    renderCampaignPage(<ConceptsPage />, 'c-gen')
    expect(await screen.findByText(/generating concepts/i)).toBeInTheDocument()
  })

  it('renders backend rich-shape concepts (channel_mix / tone_board object) without crashing', async () => {
    const richCampaign = {
      id: 'c-rich', mandate_id: 'm-x', tenant_id: 't1', status: 'concepts_ready',
      concepts: [{
        id: 'cc-1', name: 'Authenticity Wins', tagline: 'Be real, be seen',
        channel_mix: [
          { channel: 'TikTok', rationale: 'reach', competitor_gap: 'absent' },
          { channel: 'Instagram' },
        ],
        tone_board: { adjectives: ['bold', 'authentic'], visual_direction: 'vibrant, high-contrast' },
        audience_segmentation: { primary: 'Gen-Z', secondary: 'Millennials' },
        risk_flags: { legal: null, regulatory: null, sensitivity: null },
      }],
      selected_concept_id: null, activation_plan: null, budget_proposal: null,
      creative_assets: null, kpi_configs: [], created_at: '2026-05-31T00:00:00Z', updated_at: '2026-05-31T00:00:00Z',
    }
    server.use(http.get('/api/v1/campaigns/:id', () => HttpResponse.json(richCampaign)))
    renderCampaignPage(<ConceptsPage />, 'c-rich')
    await waitFor(() => {
      expect(screen.getByText('Authenticity Wins')).toBeInTheDocument()
      expect(screen.getByText('TikTok')).toBeInTheDocument()
    })
  })
})

// ── PlanPage (c-002 — planned) ────────────────────────────────────────────────

describe('PlanPage', () => {
  it('renders without crashing', () => {
    renderCampaignPage(<PlanPage />, 'c-002')
    expect(document.body).toBeInTheDocument()
  })

  it('loads activation plan channels', async () => {
    renderCampaignPage(<PlanPage />, 'c-002')
    await waitFor(() => {
      expect(screen.getByText('Google Ads')).toBeInTheDocument()
      expect(screen.getByText('LinkedIn Ads')).toBeInTheDocument()
      // Meta Ads appears twice (Feed + Stories rows)
      expect(screen.getAllByText('Meta Ads').length).toBeGreaterThanOrEqual(1)
    })
  })

  it('shows Approve Budget button', async () => {
    renderCampaignPage(<PlanPage />, 'c-002')
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /approve budget/i })).toBeInTheDocument()
    )
  })
})

// ── BudgetPage (c-003 — creative_ready with budget_proposal) ─────────────────

describe('BudgetPage', () => {
  it('renders without crashing', () => {
    renderCampaignPage(<BudgetPage />, 'c-003')
    expect(document.body).toBeInTheDocument()
  })

  it('loads budget allocation table columns', async () => {
    renderCampaignPage(<BudgetPage />, 'c-003')
    await waitFor(() => {
      expect(screen.getByText('Channel')).toBeInTheDocument()
      expect(screen.getByText('Amount')).toBeInTheDocument()
      expect(screen.getByText('Share')).toBeInTheDocument()
    })
  })
})

// ── CreativesPage (c-003 — creative_ready) ───────────────────────────────────

describe('CreativesPage', () => {
  it('renders without crashing', () => {
    renderCampaignPage(<CreativesPage />, 'c-003')
    expect(document.body).toBeInTheDocument()
  })

  it('shows Creative Assets heading', async () => {
    renderCampaignPage(<CreativesPage />, 'c-003')
    await waitFor(() => expect(screen.getByText('Creative Assets')).toBeInTheDocument())
  })

  it('renders all 4 asset tabs', async () => {
    renderCampaignPage(<CreativesPage />, 'c-003')
    await waitFor(() => {
      expect(screen.getByRole('tab', { name: 'Copy' })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: 'Scripts' })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: 'Images' })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: 'Audio' })).toBeInTheDocument()
    })
  })

  it('shows copy asset accordion items', async () => {
    renderCampaignPage(<CreativesPage />, 'c-003')
    await waitFor(() => expect(screen.getByText('Social Caption')).toBeInTheDocument())
  })
})

// ── GoLivePage (c-003 — creative_ready) ───────────────────────────────────────

describe('GoLivePage', () => {
  it('renders without crashing', () => {
    renderCampaignPage(<GoLivePage />, 'c-003')
    expect(document.body).toBeInTheDocument()
  })

  it('shows Go Live heading', async () => {
    renderCampaignPage(<GoLivePage />, 'c-003')
    await waitFor(() => expect(screen.getByText('Go Live')).toBeInTheDocument())
  })

  it('shows Campaign Summary card', async () => {
    renderCampaignPage(<GoLivePage />, 'c-003')
    await waitFor(() => expect(screen.getByText('Campaign Summary')).toBeInTheDocument())
  })

  it('shows Launch Campaign button', async () => {
    renderCampaignPage(<GoLivePage />, 'c-003')
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /launch campaign/i })).toBeInTheDocument()
    )
  })
})

// ── KpisPage (c-004 — live) ───────────────────────────────────────────────────

describe('KpisPage', () => {
  it('renders without crashing', () => {
    renderCampaignPage(<KpisPage />, 'c-004')
    expect(document.body).toBeInTheDocument()
  })

  it('shows KPI Tracking heading', async () => {
    renderCampaignPage(<KpisPage />, 'c-004')
    await waitFor(() => expect(screen.getByText('KPI Tracking')).toBeInTheDocument())
  })

  it('loads KPI rows from MSW', async () => {
    renderCampaignPage(<KpisPage />, 'c-004')
    await waitFor(() => {
      expect(screen.getByText('Clicks')).toBeInTheDocument()
      expect(screen.getByText('CTR')).toBeInTheDocument()
    })
  })

  it('shows edit buttons', async () => {
    renderCampaignPage(<KpisPage />, 'c-004')
    await waitFor(() =>
      expect(screen.getAllByRole('button').length).toBeGreaterThan(0)
    )
  })
})
