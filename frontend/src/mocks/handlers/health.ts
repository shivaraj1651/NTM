import { http, HttpResponse } from 'msw'

export const healthHandlers = [
  http.get('/api/v1/admin/health', () => {
    return HttpResponse.json({
      api: 'ok',
      db: 'ok',
      celery: 'ok',
      latency_ms: Math.floor(Math.random() * 30) + 30,
    })
  }),
]
