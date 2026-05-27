import { http, HttpResponse } from 'msw'
import { tenantsStore } from '../db'

export const tenantHandlers = [
  http.get('/api/v1/admin/tenants', () => {
    return HttpResponse.json(Object.values(tenantsStore))
  }),

  http.post('/api/v1/admin/tenants', async ({ request }) => {
    const body = await request.json() as { name: string }
    const newTenant = {
      id: `t${Date.now()}`,
      name: body.name,
      is_active: true,
      created_at: new Date().toISOString(),
    }
    // Full assignment triggers Proxy.set → persists to localStorage
    tenantsStore[newTenant.id] = newTenant
    return HttpResponse.json(newTenant, { status: 201 })
  }),

  http.patch('/api/v1/admin/tenants/:id', async ({ params, request }) => {
    const body = await request.json() as { is_active: boolean }
    const tenant = tenantsStore[params.id as string]
    if (!tenant) return new HttpResponse(null, { status: 404 })
    // Spread + reassign triggers Proxy.set → persists to localStorage
    tenantsStore[params.id as string] = { ...tenant, is_active: body.is_active }
    return HttpResponse.json(tenantsStore[params.id as string])
  }),
]
