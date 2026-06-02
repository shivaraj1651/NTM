import React from 'react'
import type { RenderResult } from '@testing-library/react'
import { render } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { useAuthStore } from '@/store/useAuthStore'

export const ADMIN_USER = {
  id: 'u-admin',
  email: 'admin@test.com',
  role: 'platform_admin',
}

export const CAMPAIGN_MANAGER_USER = {
  id: 'u-cm',
  email: 'cm@test.com',
  role: 'campaign_manager',
  tenant_id: 't1',
}

export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  })
}

interface RenderOptions {
  route?: string
  path?: string
  user?: typeof ADMIN_USER | typeof CAMPAIGN_MANAGER_USER
  queryClient?: QueryClient
}

export function renderWithProviders(
  ui: React.ReactNode,
  {
    route = '/',
    path = '/',
    user = ADMIN_USER,
    queryClient,
  }: RenderOptions = {}
): RenderResult {
  useAuthStore.setState({ token: 'test-token', user })
  const qc = queryClient ?? createTestQueryClient()
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path={path} element={<>{ui}</>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

interface NestedRenderOptions {
  route?: string
  parentPath?: string
  user?: typeof ADMIN_USER | typeof CAMPAIGN_MANAGER_USER
  queryClient?: QueryClient
}

export function renderWithNestedRoutes(
  ui: React.ReactNode,
  {
    route = '/',
    parentPath = '/',
    user = ADMIN_USER,
    queryClient,
  }: NestedRenderOptions = {}
): RenderResult {
  useAuthStore.setState({ token: 'test-token', user })
  const qc = queryClient ?? createTestQueryClient()
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path={`${parentPath}/*`} element={<>{ui}</>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

export function renderCampaignPage(
  ui: React.ReactNode,
  campaignId: string,
): RenderResult {
  useAuthStore.setState({ token: 'test-token', user: ADMIN_USER })
  const qc = createTestQueryClient()
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/admin/campaigns/${campaignId}/page`]}>
        <Routes>
          <Route path="/admin/campaigns/:id/page" element={<>{ui}</>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}
