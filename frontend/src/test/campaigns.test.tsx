import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { CampaignsPage } from '@/pages/Admin/Campaigns/CampaignsPage'
import { CampaignDetailPage } from '@/pages/Admin/Campaigns/CampaignDetailPage'
import { ConceptsPage } from '@/pages/Admin/Campaigns/ConceptsPage'
import { PlanPage } from '@/pages/Admin/Campaigns/PlanPage'
import { BudgetPage } from '@/pages/Admin/Campaigns/BudgetPage'
import { CreativesPage } from '@/pages/Admin/Campaigns/CreativesPage'
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

  it('loads all 3 seeded campaigns for tenant t1', async () => {
    renderWithProviders(<CampaignsPage />, {
      route: '/admin/campaigns',
      path: '/admin/campaigns',
      user: CAMPAIGN_MANAGER_USER,
    })
    await waitFor(() => {
      expect(screen.getByText('c-001')).toBeInTheDocument()
      expect(screen.getByText('c-002')).toBeInTheDocument()
      expect(screen.getByText('c-003')).toBeInTheDocument()
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

  it('renders all 7 stepper steps', async () => {
    renderWithProviders(<CampaignDetailPage />, {
      route: '/admin/campaigns/c-001',
      path: '/admin/campaigns/:id',
    })
    await waitFor(() => {
      for (const step of ['Create', 'Concepts', 'Confirmed', 'Plan', 'Budget', 'Approved', 'Creatives']) {
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
