import { http, HttpResponse } from 'msw'
import { creativesStore } from '../db/campaigns'

export const creativesHandlers = [
  http.get('/api/v1/creatives', ({ request }) => {
    const campaignId = new URL(request.url).searchParams.get('campaign_id')
    const all = Object.values(creativesStore) as Record<string, unknown>[]
    const filtered = campaignId
      ? all.filter((c) => c.campaign_id === campaignId)
      : all
    return HttpResponse.json({ creatives: filtered, total: filtered.length })
  }),

  http.get('/api/v1/creatives/:id', ({ params }) => {
    const creative = creativesStore[params.id as string]
    if (!creative) return HttpResponse.json({ detail: 'Not found' }, { status: 404 })
    return HttpResponse.json(creative)
  }),

  http.patch('/api/v1/creatives/:id/status', async ({ params, request }) => {
    const id = params.id as string
    const creative = creativesStore[id] as Record<string, unknown> | undefined
    if (!creative) return HttpResponse.json({ detail: 'Not found' }, { status: 404 })
    const body = await request.json() as { status: string; notes?: string }
    const updated = {
      ...creative,
      validation_status: body.status,
      status: body.status,
      notes: body.notes ?? (creative.notes as string | null) ?? null,
      updated_at: new Date().toISOString(),
    }
    creativesStore[id] = updated
    return HttpResponse.json(updated)
  }),
]
