import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { MandatesPage } from '@/pages/Mandate/MandatesPage'
import { MandateSummaryPage } from '@/pages/Mandate/MandateSummaryPage'
import { renderWithProviders, CAMPAIGN_MANAGER_USER } from './utils'

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
})
