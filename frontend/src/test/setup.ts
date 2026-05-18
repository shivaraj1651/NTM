import '@testing-library/jest-dom'
import { vi, afterEach, beforeAll, afterAll } from 'vitest'
import { cleanup } from '@testing-library/react'
import { setupServer } from 'msw/node'
import { authHandlers } from '@/mocks/handlers/auth'
import { tenantHandlers } from '@/mocks/handlers/tenants'
import { userHandlers } from '@/mocks/handlers/users'
import { roleHandlers } from '@/mocks/handlers/roles'
import { auditHandlers } from '@/mocks/handlers/audit'
import { healthHandlers } from '@/mocks/handlers/health'
import { analyticsHandlers } from '@/mocks/handlers/analytics'
import { mandateHandlers } from '@/mocks/handlers/mandates'
import { campaignHandlers } from '@/mocks/handlers/campaigns'

// Mock browser APIs absent in jsdom
global.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
}

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
})

window.HTMLElement.prototype.scrollIntoView = () => {}

Object.defineProperty(navigator, 'clipboard', {
  value: { writeText: vi.fn().mockResolvedValue(undefined) },
  writable: true,
})

export const server = setupServer(
  ...authHandlers,
  ...tenantHandlers,
  ...userHandlers,
  ...roleHandlers,
  ...auditHandlers,
  ...healthHandlers,
  ...analyticsHandlers,
  ...mandateHandlers,
  ...campaignHandlers,
)

beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }))
afterEach(() => {
  server.resetHandlers()
  cleanup()
})
afterAll(() => server.close())
