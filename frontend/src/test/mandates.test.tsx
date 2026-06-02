import { describe, it, expect } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { MandatesPage } from '@/pages/Mandate/MandatesPage'
import { MandateSummaryPage } from '@/pages/Mandate/MandateSummaryPage'
import { MandateFormPage } from '@/pages/Mandate/MandateFormPage'
import { renderWithProviders, CAMPAIGN_MANAGER_USER } from './utils'
import { server } from './setup'

function summaryCard(overrides: Record<string, unknown>) {
  return {
    id: 'm-x', name: 'Sample', tenant_id: 't1',
    total_budget: 1000, currency: 'USD', objective: 'awareness',
    region: 'EMEA', countries: ['DE'], start_date: '2026-07-01',
    end_date: '2026-09-30', created_at: '2026-05-31T00:00:00Z',
    ...overrides,
  }
}

describe('MandatesPage', () => {
  it('renders without crashing', () => {
    renderWithProviders(<MandatesPage />, {
      route: '/admin/mandates',
      path: '/admin/mandates',
      user: CAMPAIGN_MANAGER_USER,
    })
    expect(document.body).toBeInTheDocument()
  })

  it('shows Mandates heading', () => {
    renderWithProviders(<MandatesPage />, {
      route: '/admin/mandates',
      path: '/admin/mandates',
      user: CAMPAIGN_MANAGER_USER,
    })
    expect(screen.getByText('Mandates')).toBeInTheDocument()
  })

  it('loads seeded mandates for tenant t1', async () => {
    renderWithProviders(<MandatesPage />, {
      route: '/admin/mandates',
      path: '/admin/mandates',
      user: CAMPAIGN_MANAGER_USER,
    })
    await waitFor(() => {
      expect(screen.getByText('Q3 Brand Awareness')).toBeInTheDocument()
      expect(screen.getByText('Product Launch APAC')).toBeInTheDocument()
    })
  })

  it('shows New Mandate button', () => {
    renderWithProviders(<MandatesPage />, {
      route: '/admin/mandates',
      path: '/admin/mandates',
      user: CAMPAIGN_MANAGER_USER,
    })
    expect(screen.getByRole('button', { name: /new mandate/i })).toBeInTheDocument()
  })
})

describe('MandateSummaryPage', () => {
  it('renders mandate name', async () => {
    renderWithProviders(<MandateSummaryPage />, {
      route: '/admin/mandates/m-001/summary',
      path: '/admin/mandates/:id/summary',
      user: CAMPAIGN_MANAGER_USER,
    })
    await waitFor(() =>
      expect(screen.getByText('Q3 Brand Awareness')).toBeInTheDocument()
    )
  })

  it('shows objective', async () => {
    renderWithProviders(<MandateSummaryPage />, {
      route: '/admin/mandates/m-001/summary',
      path: '/admin/mandates/:id/summary',
      user: CAMPAIGN_MANAGER_USER,
    })
    await waitFor(() =>
      expect(screen.getByText('awareness')).toBeInTheDocument()
    )
  })

  it('shows Confirm and Reject buttons', async () => {
    renderWithProviders(<MandateSummaryPage />, {
      route: '/admin/mandates/m-001/summary',
      path: '/admin/mandates/:id/summary',
      user: CAMPAIGN_MANAGER_USER,
    })
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /confirm/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /reject/i })).toBeInTheDocument()
    })
  })

  it('disables Confirm while analysis is still pending', async () => {
    server.use(
      http.get('/api/v1/mandates/:id/summary-card', () =>
        HttpResponse.json(summaryCard({ id: 'm-analyzing', status: 'analyzing' })),
      ),
    )
    renderWithProviders(<MandateSummaryPage />, {
      route: '/admin/mandates/m-analyzing/summary',
      path: '/admin/mandates/:id/summary',
      user: CAMPAIGN_MANAGER_USER,
    })
    const btn = await screen.findByRole('button', { name: /confirm/i })
    expect(btn).toBeDisabled()
  })

  it('enables Confirm once the mandate is analyzed', async () => {
    server.use(
      http.get('/api/v1/mandates/:id/summary-card', () =>
        HttpResponse.json(summaryCard({ id: 'm-analyzed', status: 'analyzed' })),
      ),
    )
    renderWithProviders(<MandateSummaryPage />, {
      route: '/admin/mandates/m-analyzed/summary',
      path: '/admin/mandates/:id/summary',
      user: CAMPAIGN_MANAGER_USER,
    })
    const btn = await screen.findByRole('button', { name: /confirm/i })
    expect(btn).toBeEnabled()
  })
})

describe('MandateFormPage', () => {
  it('renders create form heading', () => {
    renderWithProviders(<MandateFormPage />, {
      route: '/admin/mandates/new',
      path: '/admin/mandates/new',
      user: CAMPAIGN_MANAGER_USER,
    })
    expect(screen.getByText('New Mandate')).toBeInTheDocument()
  })

  it('shows validation error when name is too short', async () => {
    renderWithProviders(<MandateFormPage />, {
      route: '/admin/mandates/new',
      path: '/admin/mandates/new',
      user: CAMPAIGN_MANAGER_USER,
    })
    fireEvent.change(screen.getByPlaceholderText('Q3 Brand Awareness'), { target: { value: 'ab' } })
    fireEvent.click(screen.getByRole('button', { name: /create mandate/i }))
    await waitFor(() =>
      expect(screen.getByText(/at least 3 characters/i)).toBeInTheDocument()
    )
  })
})

describe('MandateFormPage — cities', () => {
  it('does not show cities section before any country is selected', () => {
    renderWithProviders(<MandateFormPage />, {
      route: '/admin/mandates/new',
      path: '/admin/mandates/new',
      user: CAMPAIGN_MANAGER_USER,
    })
    expect(screen.queryByText('Cities')).not.toBeInTheDocument()
  })

  it('shows cities for a selected country', async () => {
    renderWithProviders(<MandateFormPage />, {
      route: '/admin/mandates/new',
      path: '/admin/mandates/new',
      user: CAMPAIGN_MANAGER_USER,
    })

    // Find the Region trigger by its placeholder text
    const regionTrigger = screen.getByText('Select region…').closest('button')!
    fireEvent.click(regionTrigger)
    // Click the radix dropdown option (span), not any native <option>
    await waitFor(() => expect(screen.getByRole('option', { name: 'APAC' })).toBeInTheDocument())
    fireEvent.click(screen.getByRole('option', { name: 'APAC' }))

    // India checkbox should appear
    await waitFor(() => expect(screen.getByLabelText('India')).toBeInTheDocument())
    fireEvent.click(screen.getByLabelText('India'))

    // Cities section with Mumbai and Delhi should appear
    await waitFor(() => {
      expect(screen.getByText('Cities')).toBeInTheDocument()
      expect(screen.getByLabelText('Mumbai')).toBeInTheDocument()
      expect(screen.getByLabelText('Delhi')).toBeInTheDocument()
    })
  })

  it('removes city checkboxes when their country is deselected', async () => {
    renderWithProviders(<MandateFormPage />, {
      route: '/admin/mandates/new',
      path: '/admin/mandates/new',
      user: CAMPAIGN_MANAGER_USER,
    })

    // Select APAC region
    const regionTrigger = screen.getByText('Select region…').closest('button')!
    fireEvent.click(regionTrigger)
    await waitFor(() => expect(screen.getByRole('option', { name: 'APAC' })).toBeInTheDocument())
    fireEvent.click(screen.getByRole('option', { name: 'APAC' }))

    // Check India, then uncheck it
    await waitFor(() => expect(screen.getByLabelText('India')).toBeInTheDocument())
    fireEvent.click(screen.getByLabelText('India'))
    await waitFor(() => expect(screen.getByLabelText('Mumbai')).toBeInTheDocument())
    fireEvent.click(screen.getByLabelText('India'))

    // Mumbai should disappear
    await waitFor(() => {
      expect(screen.queryByLabelText('Mumbai')).not.toBeInTheDocument()
    })
  })
})
