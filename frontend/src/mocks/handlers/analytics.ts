import { http, HttpResponse } from 'msw'
import { analyticsSummaries, analyticsTrends } from '../db/analytics'

export const analyticsHandlers = [
  http.get('/api/v1/analytics/summary', ({ request }) => {
    const url = new URL(request.url)
    const tenantId = url.searchParams.get('tenant_id')
    // Return first 2 mandates for t2, all 3 for any other tenant
    const results = tenantId === 't2' ? analyticsSummaries.slice(0, 2) : analyticsSummaries
    return HttpResponse.json(results)
  }),

  http.get('/api/v1/analytics/trends', ({ request }) => {
    const url = new URL(request.url)
    const days = parseInt(url.searchParams.get('days') ?? '7') || 7
    return HttpResponse.json(analyticsTrends.slice(-days))
  }),

  http.post('/api/v1/campaigns/:id/replan', ({ params }) => {
    return HttpResponse.json({ status: 'queued', job_id: `job-${params.id}-${Date.now()}` })
  }),

  http.delete('/api/v1/alerts/:id', () => {
    return new HttpResponse(null, { status: 204 })
  }),
]
