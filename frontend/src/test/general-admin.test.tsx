import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { TenantsPage } from '@/pages/Admin/Tenants/TenantsPage'
import { UsersPage } from '@/pages/Admin/Users/UsersPage'
import { RolesPage } from '@/pages/Admin/Roles/RolesPage'
import { AuditLogPage } from '@/pages/Admin/AuditLog/AuditLogPage'
import { HealthPage } from '@/pages/Admin/Health/HealthPage'
import { AnalyticsPage } from '@/pages/Admin/Analytics/AnalyticsPage'
import { renderWithProviders } from './utils'

// ── Tenants ──────────────────────────────────────────────────────────────────

describe('TenantsPage', () => {
  it('renders without crashing', () => {
    renderWithProviders(<TenantsPage />)
    expect(document.body).toBeInTheDocument()
  })

  it('shows page heading', () => {
    renderWithProviders(<TenantsPage />)
    expect(screen.getByText(/Tenants/i)).toBeInTheDocument()
  })

  it('loads all 3 seeded tenants from MSW', async () => {
    renderWithProviders(<TenantsPage />)
    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument()
      expect(screen.getByText('BrandCo')).toBeInTheDocument()
      expect(screen.getByText('MediaGroup')).toBeInTheDocument()
    })
  })

  it('shows New Tenant button', async () => {
    renderWithProviders(<TenantsPage />)
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /new tenant/i })).toBeInTheDocument()
    )
  })
})

// ── Users ────────────────────────────────────────────────────────────────────

describe('UsersPage', () => {
  it('renders without crashing', () => {
    renderWithProviders(<UsersPage />)
    expect(document.body).toBeInTheDocument()
  })

  it('shows page heading', () => {
    renderWithProviders(<UsersPage />)
    expect(screen.getByRole('heading', { name: /Users/i })).toBeInTheDocument()
  })

  it('shows tenant selector', async () => {
    renderWithProviders(<UsersPage />)
    // Radix Select renders as a button with "Select tenant" placeholder
    await waitFor(() =>
      expect(screen.getByRole('combobox')).toBeInTheDocument()
    )
  })
})

// ── Roles ────────────────────────────────────────────────────────────────────

describe('RolesPage', () => {
  it('renders without crashing', () => {
    renderWithProviders(<RolesPage />)
    expect(document.body).toBeInTheDocument()
  })

  it('shows page heading', () => {
    renderWithProviders(<RolesPage />)
    expect(screen.getByRole('heading', { name: /Roles/i })).toBeInTheDocument()
  })

  it('loads role names from MSW', async () => {
    renderWithProviders(<RolesPage />)
    await waitFor(() => {
      expect(screen.getByText('platform_admin')).toBeInTheDocument()
      expect(screen.getByText('campaign_manager')).toBeInTheDocument()
    })
  })

  it('shows Role and Permissions column headers', async () => {
    renderWithProviders(<RolesPage />)
    await waitFor(() => {
      expect(screen.getByText('Role')).toBeInTheDocument()
      expect(screen.getByText('Permissions')).toBeInTheDocument()
    })
  })
})

// ── Audit Log ────────────────────────────────────────────────────────────────

describe('AuditLogPage', () => {
  it('renders without crashing', () => {
    renderWithProviders(<AuditLogPage />)
    expect(document.body).toBeInTheDocument()
  })

  it('shows page heading', () => {
    renderWithProviders(<AuditLogPage />)
    expect(screen.getByText(/Audit/i)).toBeInTheDocument()
  })

  it('loads audit entries from MSW', async () => {
    renderWithProviders(<AuditLogPage />)
    await waitFor(() => {
      expect(screen.getAllByText('admin@ntm.com').length).toBeGreaterThan(0)
    })
  })

  it('shows Actor column header', async () => {
    renderWithProviders(<AuditLogPage />)
    await waitFor(() => expect(screen.getByText('Actor')).toBeInTheDocument())
  })
})

// ── Health ───────────────────────────────────────────────────────────────────

describe('HealthPage', () => {
  it('renders without crashing', () => {
    renderWithProviders(<HealthPage />)
    expect(document.body).toBeInTheDocument()
  })

  it('shows page heading', () => {
    renderWithProviders(<HealthPage />)
    expect(screen.getByText(/System Health/i)).toBeInTheDocument()
  })

  it('shows all 3 service status cards', async () => {
    renderWithProviders(<HealthPage />)
    await waitFor(() => {
      expect(screen.getByText('API')).toBeInTheDocument()
      expect(screen.getByText('PostgreSQL')).toBeInTheDocument()
      expect(screen.getByText('Celery Worker')).toBeInTheDocument()
    })
  })
})

// ── Analytics ────────────────────────────────────────────────────────────────

describe('AnalyticsPage', () => {
  it('renders without crashing', () => {
    renderWithProviders(<AnalyticsPage />)
    expect(document.body).toBeInTheDocument()
  })

  it('shows page heading', () => {
    renderWithProviders(<AnalyticsPage />)
    expect(screen.getByRole('heading', { name: /Analytics/i })).toBeInTheDocument()
  })

  it('shows tenant selector for platform_admin', async () => {
    renderWithProviders(<AnalyticsPage />)
    await waitFor(() => expect(screen.getByRole('combobox')).toBeInTheDocument())
  })
})
