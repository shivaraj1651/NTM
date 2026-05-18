import { http, HttpResponse } from 'msw'
import * as db from '../db/mandates'
import type { MandateCreate, MandateSummaryCard, ClientProfile } from '@/types/admin'

export const mandateHandlers = [
  http.get('/api/v1/mandates', ({ request }) => {
    const tenantId = new URL(request.url).searchParams.get('tenant_id')
    const all = Object.values(db.mandateStore)
    return HttpResponse.json(tenantId ? all.filter((m) => m.tenant_id === tenantId) : all)
  }),

  http.post('/api/v1/mandates', async ({ request }) => {
    const body = (await request.json()) as MandateCreate
    const client = db.clientStore[body.client_id]
    if (!client) return new HttpResponse(null, { status: 404 })
    const id = `m-${Date.now()}`
    const mandate: MandateSummaryCard = {
      id,
      name: body.name,
      tenant_id: client.tenant_id,
      budget: { total_budget: body.total_budget, currency: body.currency },
      geography: { regions: [body.region], markets: [], country_list: body.countries },
      created_at: new Date().toISOString(),
      objective: body.objective,
      region: body.region,
      countries: body.countries,
      start_date: body.start_date,
      end_date: body.end_date,
      status: 'pending_review',
      client,
    }
    db.mandateStore[id] = mandate
    return HttpResponse.json(mandate, { status: 201 })
  }),

  http.get('/api/v1/mandates/:id', ({ params }) => {
    const mandate = db.mandateStore[params.id as string]
    if (!mandate) return new HttpResponse(null, { status: 404 })
    return HttpResponse.json(mandate)
  }),

  http.get('/api/v1/mandates/:id/summary-card', ({ params }) => {
    const mandate = db.mandateStore[params.id as string]
    if (!mandate) return new HttpResponse(null, { status: 404 })
    return HttpResponse.json(mandate)
  }),

  http.post('/api/v1/mandates/:id/confirm', ({ params }) => {
    const mandate = db.mandateStore[params.id as string]
    if (!mandate) return new HttpResponse(null, { status: 404 })
    db.mandateStore[params.id as string] = { ...mandate, status: 'confirmed' }
    return HttpResponse.json(db.mandateStore[params.id as string])
  }),

  http.patch('/api/v1/mandates/:id', async ({ params, request }) => {
    const mandate = db.mandateStore[params.id as string]
    if (!mandate) return new HttpResponse(null, { status: 404 })
    const body = (await request.json()) as Partial<MandateCreate>
    db.mandateStore[params.id as string] = { ...mandate, ...body }
    return HttpResponse.json(db.mandateStore[params.id as string])
  }),

  http.post('/api/v1/clients', async ({ request }) => {
    const formData = await request.formData()
    const id = `cl-${Date.now()}`
    const client: ClientProfile = {
      id,
      org_name: formData.get('org_name') as string,
      industry: formData.get('industry') as string,
      logo_url: 'https://placehold.co/100x100',
      brand_guidelines_url: 'https://example.com/brand.pdf',
      competitors: JSON.parse((formData.get('competitors') as string) ?? '[]'),
      tenant_id: 't1',
      created_at: new Date().toISOString(),
    }
    db.clientStore[id] = client
    return HttpResponse.json(client, { status: 201 })
  }),
]
