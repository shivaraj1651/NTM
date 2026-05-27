import { http, HttpResponse } from 'msw'

const MOCK_CREATIVES = [
  {
    id: 'asset-001',
    campaign_id: 'campaign-001',
    asset_type: 'image',
    asset_url: 'https://placehold.co/800x600?text=Hero+Banner',
    status: 'client_review',
    message_variant: 'Variant A',
    format_spec: '1200x628px',
    notes: null,
    created_at: new Date().toISOString(),
  },
  {
    id: 'asset-002',
    campaign_id: 'campaign-001',
    asset_type: 'copy',
    asset_url: null,
    status: 'ai_draft',
    message_variant: 'Variant B',
    format_spec: 'Social caption',
    notes: 'Tone: energetic, max 280 chars',
    created_at: new Date().toISOString(),
  },
  {
    id: 'asset-003',
    campaign_id: 'campaign-001',
    asset_type: 'audio',
    asset_url: null,
    status: 'approved',
    message_variant: 'Radio VO',
    format_spec: '30s MP3',
    notes: null,
    created_at: new Date().toISOString(),
  },
] as const

export const creativesHandlers = [
  http.get('/api/v1/creatives', () => {
    return HttpResponse.json([...MOCK_CREATIVES])
  }),

  http.get('/api/v1/creatives/:id', ({ params }) => {
    const creative = MOCK_CREATIVES.find((c) => c.id === params.id)
    if (!creative) return HttpResponse.json({ detail: 'Not found' }, { status: 404 })
    return HttpResponse.json(creative)
  }),

  http.patch('/api/v1/creatives/:id/status', async ({ params, request }) => {
    const body = await request.json() as { status: string; notes?: string }
    const creative = MOCK_CREATIVES.find((c) => c.id === params.id)
    if (!creative) return HttpResponse.json({ detail: 'Not found' }, { status: 404 })
    return HttpResponse.json({ ...creative, status: body.status, notes: body.notes ?? creative.notes })
  }),
]
