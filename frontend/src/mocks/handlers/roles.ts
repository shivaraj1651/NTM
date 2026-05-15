import { http, HttpResponse } from 'msw'
import { users } from '../db'
import { ROLES } from '@/types/admin'

const ROLE_PERMISSIONS: Record<string, string[]> = {
  platform_admin:   ['*'],
  tenant_admin:     ['tenant.manage', 'user.manage', 'brand.manage'],
  brand_manager:    ['brand.manage', 'campaign.manage'],
  cmo:              ['campaign.manage', 'analytics.read'],
  creative_lead:    ['campaign.manage', 'asset.manage'],
  campaign_manager: ['campaign.manage'],
  viewer:           ['analytics.read'],
}

export const roleHandlers = [
  http.get('/api/v1/admin/roles', () => {
    const roles = ROLES.map((name, i) => ({
      id: String(i + 1),
      name,
      permissions: ROLE_PERMISSIONS[name],
      user_count: users.filter((u) => u.role === name).length,
    }))
    return HttpResponse.json(roles)
  }),
]
