import { describe, it, expect } from 'vitest'
import { renderWithProviders, ADMIN_USER } from './utils'
import { HealthPage } from '@/pages/Admin/Health/HealthPage'
import { RolesPage } from '@/pages/Admin/Roles/RolesPage'
import { TenantsPage } from '@/pages/Admin/Tenants/TenantsPage'
import { UsersPage } from '@/pages/Admin/Users/UsersPage'
import { AuditLogPage } from '@/pages/Admin/AuditLog/AuditLogPage'
import { AnalyticsPage } from '@/pages/Admin/Analytics/AnalyticsPage'

describe('HealthPage', () => {
  it('renders without crashing', () => {
    renderWithProviders(<HealthPage />, { route: '/admin/health', path: '/admin/health', user: ADMIN_USER })
    expect(document.body).toBeInTheDocument()
  })
})

describe('RolesPage', () => {
  it('renders without crashing', () => {
    renderWithProviders(<RolesPage />, { route: '/admin/roles', path: '/admin/roles', user: ADMIN_USER })
    expect(document.body).toBeInTheDocument()
  })
})

describe('TenantsPage', () => {
  it('renders without crashing', () => {
    renderWithProviders(<TenantsPage />, { route: '/admin/tenants', path: '/admin/tenants', user: ADMIN_USER })
    expect(document.body).toBeInTheDocument()
  })
})

describe('UsersPage', () => {
  it('renders without crashing', () => {
    renderWithProviders(<UsersPage />, { route: '/admin/users', path: '/admin/users', user: ADMIN_USER })
    expect(document.body).toBeInTheDocument()
  })
})

describe('AuditLogPage', () => {
  it('renders without crashing', () => {
    renderWithProviders(<AuditLogPage />, { route: '/admin/audit-log', path: '/admin/audit-log', user: ADMIN_USER })
    expect(document.body).toBeInTheDocument()
  })
})

describe('AnalyticsPage', () => {
  it('renders without crashing', () => {
    renderWithProviders(<AnalyticsPage />, { route: '/admin/analytics', path: '/admin/analytics', user: ADMIN_USER })
    expect(document.body).toBeInTheDocument()
  })
})
