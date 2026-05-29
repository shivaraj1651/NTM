import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { KPIDashboardPage } from '@/pages/KPIDashboard/KPIDashboardPage'
import { renderWithProviders, CAMPAIGN_MANAGER_USER, ADMIN_USER } from './utils'

// ── KPIDashboardPage ─────────────────────────────────────────────────────────
// CAMPAIGN_MANAGER_USER (tenant_id: t1) bypasses the tenant selector and
// triggers useAnalyticsSummary immediately — guarantees KPI cards render.

describe('KPIDashboardPage', () => {
  it('renders without crashing', () => {
    renderWithProviders(<KPIDashboardPage />, {
      route: '/admin/kpi-dashboard',
      path: '/admin/kpi-dashboard',
      user: CAMPAIGN_MANAGER_USER,
    })
    expect(document.body).toBeInTheDocument()
  })

  it('shows KPI summary stat cards', async () => {
    renderWithProviders(<KPIDashboardPage />, {
      route: '/admin/kpi-dashboard',
      path: '/admin/kpi-dashboard',
      user: CAMPAIGN_MANAGER_USER,
    })
    await waitFor(() => {
      expect(screen.getByText('Total KPIs')).toBeInTheDocument()
      expect(screen.getByText('On Track')).toBeInTheDocument()
      expect(screen.getByText('At Risk')).toBeInTheDocument()
      expect(screen.getByText('Failing')).toBeInTheDocument()
    })
  })

  it('shows tenant selector combobox for platform_admin', async () => {
    renderWithProviders(<KPIDashboardPage />, {
      route: '/admin/kpi-dashboard',
      path: '/admin/kpi-dashboard',
      user: ADMIN_USER,
    })
    await waitFor(() =>
      expect(screen.getByRole('combobox')).toBeInTheDocument()
    )
  })
})
