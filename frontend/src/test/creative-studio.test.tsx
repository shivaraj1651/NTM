import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from './setup'
import { CreativeStudioPage } from '@/pages/CreativeStudio/CreativeStudioPage'
import { AssetDetailPage } from '@/pages/CreativeStudio/AssetDetailPage'
import { ReportsPage } from '@/pages/Reports/ReportsPage'
import { SettingsPage } from '@/pages/Settings/SettingsPage'
import { renderWithProviders, ADMIN_USER, CAMPAIGN_MANAGER_USER } from './utils'

// ── shared fixtures ──────────────────────────────────────────────────────────

const MOCK_CREATIVE = {
  id: 'asset-001',
  campaign_id: 'c-003',
  creative_type: 'image',
  asset_type: 'image',
  platform: 'square',
  asset_url: 'https://example.com/img.jpg',
  status: 'ai_draft',
  validation_status: 'ai_draft',
  message_variant: 'Square Ad v1',
  notes: null,
}

// ── CreativeStudioPage ───────────────────────────────────────────────────────

describe('CreativeStudioPage', () => {
  it('renders without crashing', () => {
    server.use(
      http.get('/api/v1/creatives', () => HttpResponse.json({ creatives: [], total: 0 }))
    )
    renderWithProviders(<CreativeStudioPage />, { route: '/creative-studio', path: '/creative-studio' })
    expect(document.body).toBeInTheDocument()
  })

  it('shows empty state message when no assets exist', async () => {
    server.use(
      http.get('/api/v1/creatives', () => HttpResponse.json({ creatives: [], total: 0 }))
    )
    renderWithProviders(<CreativeStudioPage />, { route: '/creative-studio', path: '/creative-studio' })
    await waitFor(() =>
      expect(screen.getByText(/no creative assets yet/i)).toBeInTheDocument()
    )
  })

  it('shows Creative Studio heading when assets exist', async () => {
    server.use(
      http.get('/api/v1/creatives', () =>
        HttpResponse.json({ creatives: [MOCK_CREATIVE], total: 1 })
      )
    )
    renderWithProviders(<CreativeStudioPage />, { route: '/creative-studio', path: '/creative-studio' })
    await waitFor(() =>
      expect(screen.getByText('Creative Studio')).toBeInTheDocument()
    )
  })

  it('shows error state when API fails', async () => {
    server.use(
      http.get('/api/v1/creatives', () =>
        HttpResponse.json({ detail: 'server error' }, { status: 500 })
      )
    )
    renderWithProviders(<CreativeStudioPage />, { route: '/creative-studio', path: '/creative-studio' })
    await waitFor(() =>
      expect(screen.getByText(/failed to load assets/i)).toBeInTheDocument()
    )
  })

  it('shows Ad Images section when image asset is present', async () => {
    server.use(
      http.get('/api/v1/creatives', () =>
        HttpResponse.json({ creatives: [MOCK_CREATIVE], total: 1 })
      )
    )
    renderWithProviders(<CreativeStudioPage />, { route: '/creative-studio', path: '/creative-studio' })
    await waitFor(() =>
      expect(screen.getByText(/ad images/i)).toBeInTheDocument()
    )
  })
})

// ── AssetDetailPage ──────────────────────────────────────────────────────────

describe('AssetDetailPage', () => {
  it('renders without crashing', () => {
    server.use(
      http.get('/api/v1/creatives/:id', () => HttpResponse.json(MOCK_CREATIVE))
    )
    renderWithProviders(<AssetDetailPage />, {
      route: '/creative-studio/asset-001',
      path: '/creative-studio/:assetId',
    })
    expect(document.body).toBeInTheDocument()
  })

  it('shows asset title after loading', async () => {
    server.use(
      http.get('/api/v1/creatives/:id', () => HttpResponse.json(MOCK_CREATIVE))
    )
    renderWithProviders(<AssetDetailPage />, {
      route: '/creative-studio/asset-001',
      path: '/creative-studio/:assetId',
    })
    await waitFor(() =>
      expect(screen.getByText('Square Ad v1')).toBeInTheDocument()
    )
  })

  it('shows "Asset not found" on 404', async () => {
    server.use(
      http.get('/api/v1/creatives/:id', () =>
        HttpResponse.json({ detail: 'Not found' }, { status: 404 })
      )
    )
    renderWithProviders(<AssetDetailPage />, {
      route: '/creative-studio/missing',
      path: '/creative-studio/:assetId',
    })
    await waitFor(() =>
      expect(screen.getByText(/asset not found/i)).toBeInTheDocument()
    )
  })

  it('shows Approve and Reject buttons for platform_admin', async () => {
    server.use(
      http.get('/api/v1/creatives/:id', () => HttpResponse.json(MOCK_CREATIVE))
    )
    renderWithProviders(<AssetDetailPage />, {
      route: '/creative-studio/asset-001',
      path: '/creative-studio/:assetId',
      user: ADMIN_USER,
    })
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /approve/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /reject/i })).toBeInTheDocument()
    })
  })

  it('shows Back to Studio button', async () => {
    server.use(
      http.get('/api/v1/creatives/:id', () => HttpResponse.json(MOCK_CREATIVE))
    )
    renderWithProviders(<AssetDetailPage />, {
      route: '/creative-studio/asset-001',
      path: '/creative-studio/:assetId',
    })
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /back to studio/i })).toBeInTheDocument()
    )
  })
})

// ── ReportsPage ──────────────────────────────────────────────────────────────

describe('ReportsPage', () => {
  it('renders without crashing', () => {
    renderWithProviders(<ReportsPage />, {
      route: '/reports',
      path: '/reports',
      user: CAMPAIGN_MANAGER_USER,
    })
    expect(document.body).toBeInTheDocument()
  })

  it('shows Reports heading', () => {
    renderWithProviders(<ReportsPage />, {
      route: '/reports',
      path: '/reports',
      user: CAMPAIGN_MANAGER_USER,
    })
    expect(screen.getByRole('heading', { name: /reports/i })).toBeInTheDocument()
  })

  it('shows prompt to select a campaign when none is selected', () => {
    renderWithProviders(<ReportsPage />, {
      route: '/reports',
      path: '/reports',
      user: CAMPAIGN_MANAGER_USER,
    })
    expect(screen.getByText(/select a campaign above to view its report/i)).toBeInTheDocument()
  })

  it('loads campaign list into the selector', async () => {
    renderWithProviders(<ReportsPage />, {
      route: '/reports',
      path: '/reports',
      user: CAMPAIGN_MANAGER_USER,
    })
    await waitFor(() =>
      expect(screen.getByRole('combobox')).toBeInTheDocument()
    )
  })
})

// ── SettingsPage ─────────────────────────────────────────────────────────────

describe('SettingsPage', () => {
  it('renders without crashing', () => {
    renderWithProviders(<SettingsPage />, { route: '/settings', path: '/settings' })
    expect(document.body).toBeInTheDocument()
  })

  it('shows Settings heading', () => {
    renderWithProviders(<SettingsPage />, { route: '/settings', path: '/settings' })
    expect(screen.getByRole('heading', { name: /settings/i })).toBeInTheDocument()
  })

  it('shows user email from auth store', () => {
    renderWithProviders(<SettingsPage />, {
      route: '/settings',
      path: '/settings',
      user: ADMIN_USER,
    })
    expect(screen.getByText('admin@test.com')).toBeInTheDocument()
  })

  it('shows user role as badge', () => {
    renderWithProviders(<SettingsPage />, {
      route: '/settings',
      path: '/settings',
      user: ADMIN_USER,
    })
    expect(screen.getByText('platform admin')).toBeInTheDocument()
  })

  it('shows Save preferences button', () => {
    renderWithProviders(<SettingsPage />, { route: '/settings', path: '/settings' })
    expect(screen.getByRole('button', { name: /save preferences/i })).toBeInTheDocument()
  })

  it('shows Update password button', () => {
    renderWithProviders(<SettingsPage />, { route: '/settings', path: '/settings' })
    expect(screen.getByRole('button', { name: /update password/i })).toBeInTheDocument()
  })

  it('shows error when new passwords do not match', async () => {
    renderWithProviders(<SettingsPage />, { route: '/settings', path: '/settings' })
    await userEvent.type(screen.getByLabelText(/current password/i), 'old-pass')
    await userEvent.type(screen.getByLabelText(/^new password/i), 'newpass1')
    await userEvent.type(screen.getByLabelText(/confirm new password/i), 'different')
    await userEvent.click(screen.getByRole('button', { name: /update password/i }))
    await waitFor(() =>
      expect(screen.getByText(/do not match/i)).toBeInTheDocument()
    )
  })

  it('shows error when new password is too short', async () => {
    renderWithProviders(<SettingsPage />, { route: '/settings', path: '/settings' })
    await userEvent.type(screen.getByLabelText(/current password/i), 'old-pass')
    await userEvent.type(screen.getByLabelText(/^new password/i), 'short')
    await userEvent.type(screen.getByLabelText(/confirm new password/i), 'short')
    await userEvent.click(screen.getByRole('button', { name: /update password/i }))
    await waitFor(() =>
      expect(screen.getByText(/at least 8 characters/i)).toBeInTheDocument()
    )
  })
})
