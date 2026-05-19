import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { render } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { renderWithProviders, ADMIN_USER } from './utils'
import { useAuthStore } from '@/store/useAuthStore'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { PageHeader } from '@/components/PageHeader'

// ── ProtectedRoute ────────────────────────────────────────────────────────────

describe('ProtectedRoute', () => {
  it('redirects to /login when unauthenticated', async () => {
    useAuthStore.setState({ token: null, user: null })

    render(
      <MemoryRouter initialEntries={['/protected']}>
        <Routes>
          <Route
            path="/protected"
            element={
              <ProtectedRoute>
                <div>Protected Content</div>
              </ProtectedRoute>
            }
          />
          <Route path="/login" element={<div>Login Page</div>} />
          <Route path="/403" element={<div>Forbidden</div>} />
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
    })
  })

  it('renders outlet when authenticated as admin', async () => {
    useAuthStore.setState({ token: 'test-token', user: ADMIN_USER })

    render(
      <MemoryRouter initialEntries={['/protected']}>
        <Routes>
          <Route element={<ProtectedRoute />}>
            <Route path="/protected" element={<div>Admin Content</div>} />
          </Route>
          <Route path="/login" element={<div>Login Page</div>} />
          <Route path="/403" element={<div>Forbidden</div>} />
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Admin Content')).toBeInTheDocument()
    })
  })
})

// ── PageHeader ────────────────────────────────────────────────────────────────

describe('PageHeader', () => {
  it('renders title', () => {
    render(<PageHeader title="Test Page" />)
    expect(screen.getByText('Test Page')).toBeInTheDocument()
  })

  it('renders description when provided', () => {
    render(<PageHeader title="Test" description="A description" />)
    expect(screen.getByText('A description')).toBeInTheDocument()
  })
})

// ── Sidebar ───────────────────────────────────────────────────────────────────

describe('Sidebar', () => {
  it('renders NTM Admin heading', async () => {
    useAuthStore.setState({ token: 'test-token', user: ADMIN_USER })
    const { Sidebar } = await import('@/components/Sidebar')
    renderWithProviders(<Sidebar />, { route: '/admin', path: '/admin', user: ADMIN_USER })
    await waitFor(() => {
      expect(screen.getByText(/ntm admin/i)).toBeInTheDocument()
    })
  })
})
