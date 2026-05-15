import { http, HttpResponse } from 'msw'
import { analyticsSummaries, analyticsTrends } from '../db/analytics'

export const analyticsHandlers = [
  http.get('/api/v1/analytics/summary', () => {
    return HttpResponse.json(analyticsSummaries)
  }),

  http.get('/api/v1/analytics/trends', ({ request }) => {
    const url = new URL(request.url)
    const days = parseInt(url.searchParams.get('days') ?? '7')
    return HttpResponse.json(analyticsTrends.slice(-days))
  }),

  http.post('/api/v1/campaigns/:id/replan', ({ params }) => {
    return HttpResponse.json({ status: 'queued', job_id: `job-${params.id}-${Date.now()}` })
  }),

  http.delete('/api/v1/alerts/:id', () => {
    return new HttpResponse(null, { status: 204 })
  }),
]
