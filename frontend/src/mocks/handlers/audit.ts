import { http, HttpResponse } from 'msw'
import { auditEntries } from '../db'

export const auditHandlers = [
  http.get('/api/v1/admin/audit', ({ request }) => {
    const url = new URL(request.url)
    const entity_type = url.searchParams.get('entity_type')
    const actor = url.searchParams.get('actor')
    const from = url.searchParams.get('from')
    const to = url.searchParams.get('to')

    let results = [...auditEntries]
    if (entity_type) results = results.filter((e) => e.entity_type === entity_type)
    if (actor) results = results.filter((e) => e.actor.includes(actor))
    if (from) results = results.filter((e) => e.timestamp >= from)
    if (to) results = results.filter((e) => e.timestamp <= to.slice(0, 10) + 'T23:59:59Z')

    return HttpResponse.json(results)
  }),
]
