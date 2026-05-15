import { setupWorker } from 'msw/browser'
import { authHandlers } from './handlers/auth'
import { tenantHandlers } from './handlers/tenants'
import { userHandlers } from './handlers/users'
import { roleHandlers } from './handlers/roles'
import { auditHandlers } from './handlers/audit'
import { healthHandlers } from './handlers/health'
import { analyticsHandlers } from './handlers/analytics'

export const worker = setupWorker(
  ...authHandlers,
  ...tenantHandlers,
  ...userHandlers,
  ...roleHandlers,
  ...auditHandlers,
  ...healthHandlers,
  ...analyticsHandlers,
)
