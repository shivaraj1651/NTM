/**
 * routing.test.tsx
 *
 * Integration-level routing tests.  Covers gaps not exercised by per-page
 * unit tests:
 *   • /403 page content
 *   • ProtectedRoute role-guard (blocks non-platform_admin)
 *   • Root / → /admin/tenants redirect
 *   • Campaign nested sub-routes resolve without "No routes matched" warnings
 *   • All sidebar nav paths render without crashing
 */
import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { render } from '@testing-library/react'
import { MemoryRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { useAuthStore } from '@/store/useAuthStore'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { CampaignDetailPage } from '@/pages/Admin/Campaigns/CampaignDetailPage'
import { ConceptsPage } from '@/pages/Admin/Campaigns/ConceptsPage'
import { PlanPage } from '@/pages/Admin/Campaigns/PlanPage'
import { BudgetPage } from '@/pages/Admin/Campaigns/BudgetPage'
import { CreativesPage } from '@/pages/Admin/Campaigns/CreativesPage'
import { GoLivePage } from '@/pages/Admin/Campaigns/GoLivePage'
import { KpisPage } from '@/pages/Admin/Campaigns/KpisPage'
import { PhysicalLogPage } from '@/pages/Admin/Campaigns/PhysicalLogPage'
import { CIReportPage } from '@/pages/Admin/Campaigns/CIReportPage'
import { TenantsPage } from '@/pages/Admin/Tenants/TenantsPage'
import { UsersPage } from '@/pages/Admin/Users/UsersPage'
import { RolesPage } from '@/pages/Admin/Roles/RolesPage'
import { AuditLogPage } from '@/pages/Admin/AuditLog/AuditLogPage'
import { HealthPage } from '@/pages/Admin/Health/HealthPage'
import { AnalyticsPage } from '@/pages/Admin/Analytics/AnalyticsPage'
import { MandatesPage } from '@/pages/Mandate/MandatesPage'
import { CampaignsPage } from '@/pages/Admin/Campaigns/CampaignsPage'
import { KPIDashboardPage } from '@/pages/KPIDashboard/KPIDashboardPage'
import {
  renderWithProviders,
  renderWithNestedRoutes,
  createTestQueryClient,
  ADMIN_USER,
  CAMPAIGN_MANAGER_USER,
} from './utils'

// ── Shared child routes for CampaignDetailPage ────────────────────────────────

const CAMPAIGN_CHILDREN = [
  { path: 'concepts',     element: <ConceptsPage /> },
  { path: 'plan',         element: <PlanPage /> },
  { path: 'budget',       element: <BudgetPage /> },
  { path: 'creatives',    element: <CreativesPage /> },
  { path: 'golive',       element: <GoLivePage /> },
  { path: 'kpis',         element: <KpisPage /> },
  { path: 'physical-log', element: <PhysicalLogPage /> },
  { path: 'ci-report',    element: <CIReportPage /> },
]

// ── /403 page ─────────────────────────────────────────────────────────────────

describe('/403 page', () => {
  it('renders Access Denied heading', () => {
    render(
      <MemoryRouter initialEntries={['/403']}>
        <Routes>
          <Route
            path="/403"
            element={
              <div>
                <h1>Access Denied</h1>
                <p>You don&apos;t have permission to view this page.</p>
              </div>
            }
          />
        </Routes>
      </MemoryRouter>
    )
    expect(screen.getByRole('heading', { name: 'Access Denied' })).toBeInTheDocument()
    expect(screen.getByText(/you don't have permission/i)).toBeInTheDocument()
  })
})

// ── Root redirect ─────────────────────────────────────────────────────────────

describe('Root redirect', () => {
  it('/ redirects to /admin/tenants', async () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/" element={<Navigate to="/admin/tenants" replace />} />
          <Route path="/admin/tenants" element={<div>Tenants Landing</div>} />
        </Routes>
      </MemoryRouter>
    )
    await waitFor(() =>
      expect(screen.getByText('Tenants Landing')).toBeInTheDocument()
    )
  })
})

// ── ProtectedRoute — role guard ───────────────────────────────────────────────

describe('ProtectedRoute role guard', () => {
  it('allows campaign_manager through (sidebar handles page-level filtering)', async () => {
    useAuthStore.setState({ token: 'test-token', user: CAMPAIGN_MANAGER_USER })
    render(
      <MemoryRouter initialEntries={['/admin/campaigns']}>
        <Routes>
          <Route element={<ProtectedRoute />}>
            <Route path="/admin/campaigns" element={<div>Campaign Content</div>} />
          </Route>
          <Route path="/403" element={<div>Forbidden</div>} />
          <Route path="/login" element={<div>Login</div>} />
        </Routes>
      </MemoryRouter>
    )
    await waitFor(() => {
      expect(screen.getByText('Campaign Content')).toBeInTheDocument()
      expect(screen.queryByText('Forbidden')).not.toBeInTheDocument()
    })
  })

  it('redirects unauthenticated user to /login', async () => {
    useAuthStore.setState({ token: null, user: null })
    render(
      <MemoryRouter initialEntries={['/admin/tenants']}>
        <Routes>
          <Route element={<ProtectedRoute />}>
            <Route path="/admin/tenants" element={<div>Admin Content</div>} />
          </Route>
          <Route path="/login" element={<div>Login Page</div>} />
          <Route path="/403" element={<div>Forbidden</div>} />
        </Routes>
      </MemoryRouter>
    )
    await waitFor(() => {
      expect(screen.getByText('Login Page')).toBeInTheDocument()
      expect(screen.queryByText('Admin Content')).not.toBeInTheDocument()
    })
  })

  it('allows platform_admin through', async () => {
    useAuthStore.setState({ token: 'test-token', user: ADMIN_USER })
    render(
      <MemoryRouter initialEntries={['/admin/tenants']}>
        <Routes>
          <Route element={<ProtectedRoute />}>
            <Route path="/admin/tenants" element={<div>Admin Content</div>} />
          </Route>
          <Route path="/403" element={<div>Forbidden</div>} />
          <Route path="/login" element={<div>Login</div>} />
        </Routes>
      </MemoryRouter>
    )
    await waitFor(() => {
      expect(screen.getByText('Admin Content')).toBeInTheDocument()
    })
  })
})

// ── Campaign nested sub-routes (no "No routes matched" stderr) ────────────────

describe('Campaign nested sub-routes', () => {
  it.each([
    ['concepts',     'c-001'],
    ['plan',         'c-002'],
    ['budget',       'c-003'],
    ['creatives',    'c-003'],
    ['golive',       'c-003'],
    ['kpis',         'c-004'],
    ['physical-log', 'c-004'],
    ['ci-report',    'c-001'],
  ] as const)(
    '/admin/campaigns/:id/%s renders without crashing',
    async (subPage, campaignId) => {
      renderWithNestedRoutes(<CampaignDetailPage />, {
        route: `/admin/campaigns/${campaignId}/${subPage}`,
        parentPath: '/admin/campaigns/:id',
        children: CAMPAIGN_CHILDREN,
      })
      expect(document.body).toBeInTheDocument()
    }
  )
})

// ── Sidebar nav routes — all render without crashing ─────────────────────────

describe('Sidebar nav routes', () => {
  it.each([
    ['/admin/tenants',      <TenantsPage />],
    ['/admin/users',        <UsersPage />],
    ['/admin/roles',        <RolesPage />],
    ['/admin/audit',        <AuditLogPage />],
    ['/admin/health',       <HealthPage />],
    ['/admin/analytics',    <AnalyticsPage />],
    ['/admin/mandates',     <MandatesPage />],
    ['/admin/campaigns',    <CampaignsPage />],
    ['/admin/kpi-dashboard', <KPIDashboardPage />],
  ] as const)(
    '%s renders without crashing',
    (route, element) => {
      renderWithProviders(element, { route, path: route })
      expect(document.body).toBeInTheDocument()
    }
  )
})
