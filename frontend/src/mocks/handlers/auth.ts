import { http, HttpResponse } from 'msw'

export const authHandlers = [
  http.post('/api/v1/auth/login', async ({ request }) => {
    const body = await request.json() as { email: string; password: string }
    const isCampaignManager = body.email.includes('manager')
    return HttpResponse.json({
      token: 'mock-jwt-token',
      user: {
        id: isCampaignManager ? 'cm-1' : 'admin-1',
        email: body.email,
        role: isCampaignManager ? 'campaign_manager' : 'platform_admin',
        tenant_id: isCampaignManager ? 't1' : undefined,
      },
    })
  }),
]
