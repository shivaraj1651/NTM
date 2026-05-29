import { http, HttpResponse } from 'msw'
import { auditEntries } from '../db'

export const auditHandlers = [
  // updated path from /admin/audit → /admin/audit-log to match backend
  http.get('/api/v1/admin/audit-log', ({ request }) => {
    const url = new URL(request.url)
    const tenant_id = url.searchParams.get('tenant_id')
    const limit = parseInt(url.searchParams.get('limit') ?? '50', 10)
    const offset = parseInt(url.searchParams.get('offset') ?? '0', 10)

    let results = [...auditEntries]
    if (tenant_id) results = results.filter((e) => e.tenant_id === tenant_id)

    return HttpResponse.json(results.slice(offset, offset + limit))
  }),
]
