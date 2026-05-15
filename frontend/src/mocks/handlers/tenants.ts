import { http, HttpResponse } from 'msw'
import { tenants } from '../db'

export const tenantHandlers = [
  http.get('/api/v1/admin/tenants', () => {
    return HttpResponse.json([...tenants])
  }),

  http.post('/api/v1/admin/tenants', async ({ request }) => {
    const body = await request.json() as { name: string }
    const newTenant = {
      id: `t${Date.now()}`,
      name: body.name,
      is_active: true,
      created_at: new Date().toISOString(),
    }
    tenants.push(newTenant)
    return HttpResponse.json(newTenant, { status: 201 })
  }),

  http.patch('/api/v1/admin/tenants/:id', async ({ params, request }) => {
    const body = await request.json() as { is_active: boolean }
    const tenant = tenants.find((t) => t.id === params.id)
    if (!tenant) return new HttpResponse(null, { status: 404 })
    tenant.is_active = body.is_active
    return HttpResponse.json(tenant)
  }),
]
