import { http, HttpResponse } from 'msw'
import { usersStore } from '../db'

export const userHandlers = [
  http.get('/api/v1/admin/tenants/:tenantId/users', ({ params }) => {
    return HttpResponse.json(
      Object.values(usersStore).filter((u) => u.tenant_id === params.tenantId)
    )
  }),

  http.post('/api/v1/admin/tenants/:tenantId/users', async ({ params, request }) => {
    const body = await request.json() as { email: string; password: string; role: string }
    const newUser = {
      id: `u${Date.now()}`,
      email: body.email,
      role: body.role,
      is_active: true,
      tenant_id: params.tenantId as string,
      created_at: new Date().toISOString(),
    }
    // Full assignment triggers Proxy.set → persists to localStorage
    usersStore[newUser.id] = newUser
    return HttpResponse.json(newUser, { status: 201 })
  }),

  http.patch('/api/v1/admin/users/:id', async ({ params, request }) => {
    const body = await request.json() as { is_active: boolean }
    const user = usersStore[params.id as string]
    if (!user) return new HttpResponse(null, { status: 404 })
    // Spread + reassign triggers Proxy.set → persists to localStorage
    usersStore[params.id as string] = { ...user, is_active: body.is_active }
    return HttpResponse.json(usersStore[params.id as string])
  }),
]
