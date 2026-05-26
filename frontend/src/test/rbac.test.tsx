/**
 * RBAC — role-based access, badge colours, sidebar filtering, auth mock
 */
import { describe, it, expect } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { renderWithProviders, ADMIN_USER, CAMPAIGN_MANAGER_USER } from './utils'
import { useAuthStore } from '@/store/useAuthStore'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import React from 'react'

// ── helpers ───────────────────────────────────────────────────────────────────

function makeUser(role: string, tenant_id?: string) {
  return { id: `u-${role}`, email: `${role}@test.com`, role, tenant_id }
}

function renderProtected(user: ReturnType<typeof makeUser> | null, content = 'Protected Content') {
  useAuthStore.setState({ token: user ? 'tok' : null, user })
  return render(
    <MemoryRouter initialEntries={['/protected']}>
      <Routes>
        <Route element={<ProtectedRoute />}>
          <Route path="/protected" element={<div>{content}</div>} />
        </Route>
        <Route path="/login" element={<div>Login Page</div>} />
        <Route path="/403"   element={<div>Forbidden</div>} />
        <Route path="/admin/mandates" element={<div>Mandates Page</div>} />
      </Routes>
    </MemoryRouter>
  )
}

// ── ProtectedRoute — tiered access ────────────────────────────────────────────

describe('ProtectedRoute — access control', () => {
  it('blocks unauthenticated user → redirects to /login', async () => {
    renderProtected(null)
    await waitFor(() => expect(screen.getByText('Login Page')).toBeInTheDocument())
  })

  it('allows platform_admin through', async () => {
    renderProtected(makeUser('platform_admin'))
    await waitFor(() => expect(screen.getByText('Protected Content')).toBeInTheDocument())
  })

  it('allows tenant_admin through', async () => {
    renderProtected(makeUser('tenant_admin', 't1'))
    await waitFor(() => expect(screen.getByText('Protected Content')).toBeInTheDocument())
  })

  it('allows campaign_manager through', async () => {
    renderProtected(makeUser('campaign_manager', 't1'))
    await waitFor(() => expect(screen.getByText('Protected Content')).toBeInTheDocument())
  })

  it('allows brand_manager through', async () => {
    renderProtected(makeUser('brand_manager', 't1'))
    await waitFor(() => expect(screen.getByText('Protected Content')).toBeInTheDocument())
  })

  it('allows cmo through', async () => {
    renderProtected(makeUser('cmo', 't1'))
    await waitFor(() => expect(screen.getByText('Protected Content')).toBeInTheDocument())
  })

  it('allows viewer through', async () => {
    renderProtected(makeUser('viewer', 't1'))
    await waitFor(() => expect(screen.getByText('Protected Content')).toBeInTheDocument())
  })
})

// ── RoleBadge — colour differentiation ───────────────────────────────────────

describe('RoleBadge', () => {
  it('renders the role name', async () => {
    const { RoleBadge } = await import('@/components/RoleBadge')
    render(<RoleBadge role="platform_admin" />)
    expect(screen.getByText('platform_admin')).toBeInTheDocument()
  })

  it('renders all 7 roles without throwing', async () => {
    const { RoleBadge } = await import('@/components/RoleBadge')
    const roles = ['platform_admin','tenant_admin','brand_manager','cmo','creative_lead','campaign_manager','viewer']
    for (const role of roles) {
      const { unmount } = render(<RoleBadge role={role} />)
      expect(screen.getByText(role)).toBeInTheDocument()
      unmount()
    }
  })

  it('gives platform_admin a distinct data-role attribute', async () => {
    const { RoleBadge } = await import('@/components/RoleBadge')
    const { container } = render(<RoleBadge role="platform_admin" />)
    expect(container.querySelector('[data-role="platform_admin"]')).toBeInTheDocument()
  })

  it('gives viewer a distinct data-role attribute from platform_admin', async () => {
    const { RoleBadge } = await import('@/components/RoleBadge')
    const { container: c1 } = render(<RoleBadge role="platform_admin" />)
    const { container: c2 } = render(<RoleBadge role="viewer" />)
    const adminClass = c1.querySelector('[data-role]')?.className
    const viewerClass = c2.querySelector('[data-role]')?.className
    expect(adminClass).not.toBe(viewerClass)
  })
})

// ── Sidebar — role-filtered navigation ───────────────────────────────────────

describe('Sidebar — platform_admin sees all nav items', () => {
  it('shows Tenants link', async () => {
    const { Sidebar } = await import('@/components/Sidebar')
    renderWithProviders(<Sidebar />, { route: '/admin', path: '/admin', user: ADMIN_USER })
    await waitFor(() => expect(screen.getByText('Tenants')).toBeInTheDocument())
  })

  it('shows Users link', async () => {
    const { Sidebar } = await import('@/components/Sidebar')
    renderWithProviders(<Sidebar />, { route: '/admin', path: '/admin', user: ADMIN_USER })
    await waitFor(() => expect(screen.getByText('Users')).toBeInTheDocument())
  })

  it('shows Roles link', async () => {
    const { Sidebar } = await import('@/components/Sidebar')
    renderWithProviders(<Sidebar />, { route: '/admin', path: '/admin', user: ADMIN_USER })
    await waitFor(() => expect(screen.getByText('Roles')).toBeInTheDocument())
  })
})

describe('Sidebar — campaign_manager sees only campaign nav items', () => {
  it('shows Campaigns link', async () => {
    const { Sidebar } = await import('@/components/Sidebar')
    renderWithProviders(<Sidebar />, { route: '/admin', path: '/admin', user: CAMPAIGN_MANAGER_USER })
    await waitFor(() => expect(screen.getByText('Campaigns')).toBeInTheDocument())
  })

  it('hides Tenants link', async () => {
    const { Sidebar } = await import('@/components/Sidebar')
    renderWithProviders(<Sidebar />, { route: '/admin', path: '/admin', user: CAMPAIGN_MANAGER_USER })
    await waitFor(() => expect(screen.queryByText('Tenants')).not.toBeInTheDocument())
  })

  it('hides Users link', async () => {
    const { Sidebar } = await import('@/components/Sidebar')
    renderWithProviders(<Sidebar />, { route: '/admin', path: '/admin', user: CAMPAIGN_MANAGER_USER })
    await waitFor(() => expect(screen.queryByText('Users')).not.toBeInTheDocument())
  })

  it('hides Roles link', async () => {
    const { Sidebar } = await import('@/components/Sidebar')
    renderWithProviders(<Sidebar />, { route: '/admin', path: '/admin', user: CAMPAIGN_MANAGER_USER })
    await waitFor(() => expect(screen.queryByText('Roles')).not.toBeInTheDocument())
  })
})

// ── UsersPage — role badge display ────────────────────────────────────────────

describe('UsersPage — role badges', () => {
  it('renders page with New User button and tenant selector', async () => {
    const { UsersPage } = await import('@/pages/Admin/Users/UsersPage')
    renderWithProviders(
      <UsersPage />,
      { route: '/admin/users', path: '/admin/users', user: ADMIN_USER }
    )
    // New User button is disabled until a tenant is selected — it exists but is disabled
    await waitFor(() => expect(screen.getByRole('button', { name: /new user/i })).toBeInTheDocument())
  })

  it('prompts to select a tenant before showing users', async () => {
    const { UsersPage } = await import('@/pages/Admin/Users/UsersPage')
    renderWithProviders(
      <UsersPage />,
      { route: '/admin/users', path: '/admin/users', user: ADMIN_USER }
    )
    await waitFor(() =>
      expect(screen.getByText(/select a tenant to view its users/i)).toBeInTheDocument()
    )
  })
})
