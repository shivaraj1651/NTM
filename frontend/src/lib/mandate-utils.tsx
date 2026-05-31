import { Badge } from '@/components/ui/badge'
import type { MandateStatus } from '@/types/admin'

export function MandateStatusBadge({ status }: { status: MandateStatus }) {
  if (status === 'confirmed') return <Badge variant="default">Confirmed</Badge>
  if (status === 'rejected') return <Badge variant="destructive">Rejected</Badge>
  if (status === 'draft') return <Badge variant="secondary">Draft</Badge>
  if (status === 'analyzing') return <Badge variant="secondary">Analyzing…</Badge>
  if (status === 'analyzed') return <Badge variant="outline">Analyzed</Badge>
  return <Badge variant="outline">Pending Review</Badge>
}
