import { http, HttpResponse } from 'msw'
import { users } from '../db'

/**
 * Maps email → role for unknown (non-seed) addresses.
 * Checked in order — first match wins.
 */
const KEYWORD_ROLE: Array<{ keyword: string; role: string; tenant_id?: string }> = [
  { keyword: 'admin',    role: 'platform_admin' },
  { keyword: 'super',    role: 'platform_admin' },
  { keyword: 'tenant',   role: 'tenant_admin',     tenant_id: 't1' },
  { keyword: 'cmo',      role: 'cmo',              tenant_id: 't1' },
  { keyword: 'brand',    role: 'brand_manager',    tenant_id: 't1' },
  { keyword: 'creative', role: 'creative_lead',    tenant_id: 't1' },
  { keyword: 'manager',  role: 'campaign_manager', tenant_id: 't1' },
]

function resolveRole(email: string): { role: string; tenant_id?: string } {
  // 1. Look up known seed users first
  const seed = users.find((u) => u.email === email)
  if (seed) return { role: seed.role, tenant_id: seed.tenant_id }

  // 2. Keyword match
  const lower = email.toLowerCase()
  for (const { keyword, role, tenant_id } of KEYWORD_ROLE) {
    if (lower.includes(keyword)) return { role, tenant_id }
  }

  // 3. Default
  return { role: 'viewer', tenant_id: 't1' }
}

export const authHandlers = [
  http.post('/api/v1/auth/login', async ({ request }) => {
    const body = await request.json() as { email: string; password: string }
    const { role, tenant_id } = resolveRole(body.email)
    return HttpResponse.json({
      token: 'mock-jwt-token',
      user: {
        id: `user-${role}`,
        email: body.email,
        role,
        tenant_id,
      },
    })
  }),
]
