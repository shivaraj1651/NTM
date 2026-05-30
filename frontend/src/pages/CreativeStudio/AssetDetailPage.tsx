import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { PageHeader } from '@/components/PageHeader'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { useCreative, useUpdateCreativeStatus, type Creative } from '@/hooks/useCreatives'
import { useAuthStore } from '@/store/useAuthStore'

const STATUS_BADGE: Record<NonNullable<Creative['status']>, { label: string; className: string }> = {
  ai_draft:           { label: 'AI Draft',           className: 'bg-gray-100 text-gray-700' },
  internal_review:    { label: 'Internal Review',    className: 'bg-yellow-100 text-yellow-700' },
  client_review:      { label: 'Client Review',      className: 'bg-blue-100 text-blue-700' },
  approved:           { label: 'Approved',            className: 'bg-green-100 text-green-700' },
  revision_requested: { label: 'Revision Requested', className: 'bg-orange-100 text-orange-700' },
  rejected:           { label: 'Rejected',            className: 'bg-red-100 text-red-700' },
}

const APPROVAL_ROLES = ['creative_lead', 'brand_manager', 'cmo', 'tenant_admin', 'platform_admin']

export function AssetDetailPage() {
  const { assetId } = useParams<{ assetId: string }>()
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const [revisionNote, setRevisionNote] = useState('')

  const { data: asset, isLoading } = useCreative(assetId!)
  const { mutate: updateStatus, isPending } = useUpdateCreativeStatus()

  const canApprove = user ? APPROVAL_ROLES.includes(user.role) : false

  const handleApprove = () => {
    updateStatus({ id: assetId!, status: 'approved' }, { onSuccess: () => navigate('/creative-studio') })
  }

  const handleRequestRevision = () => {
    if (!revisionNote.trim()) return
    updateStatus(
      { id: assetId!, status: 'revision_requested', notes: revisionNote },
      { onSuccess: () => navigate('/creative-studio') }
    )
  }

  const handleReject = () => {
    updateStatus({ id: assetId!, status: 'rejected' }, { onSuccess: () => navigate('/creative-studio') })
  }

  if (isLoading) return <div className="p-8 text-muted-foreground">Loading asset…</div>
  if (!asset)   return <div className="p-8 text-destructive">Asset not found.</div>

  // Resolve fields — backend uses validation_status/creative_type/content; MSW mocks use status/asset_type/asset_url
  const statusKey = asset.status ?? (asset.validation_status as NonNullable<Creative['status']> | undefined)
  const typeKey = asset.asset_type ?? (asset.creative_type as NonNullable<Creative['asset_type']> | undefined)
  const displayUrl = asset.asset_url ?? (asset.content as Record<string, unknown> | undefined)?.['url'] as string | undefined
  const displayTitle = asset.message_variant ?? asset.id
  const displayDesc = `${typeKey ?? '—'} · ${asset.format_spec ?? asset.platform ?? '—'}`
  const badge = statusKey ? STATUS_BADGE[statusKey] : undefined
  const bodyText = asset.notes ?? (asset.content as Record<string, unknown> | undefined)?.['body'] as string | undefined

  return (
    <div className="p-6 space-y-6 max-w-3xl mx-auto">
      <PageHeader
        title={displayTitle}
        description={displayDesc}
      />

      {badge
        ? <Badge className={badge.className}>{badge.label}</Badge>
        : asset.validation_status
          ? <Badge variant="outline">{asset.validation_status}</Badge>
          : null
      }

      <Card>
        <CardContent className="pt-6">
          {typeKey === 'image' && displayUrl && (
            <img src={displayUrl} alt={displayTitle} className="w-full rounded" />
          )}
          {typeKey === 'audio' && displayUrl && (
            <audio controls src={displayUrl} className="w-full" />
          )}
          {typeKey === 'video' && displayUrl && (
            <video controls src={displayUrl} className="w-full rounded" />
          )}
          {(typeKey === 'copy' || typeKey === 'script') && (
            <pre className="whitespace-pre-wrap text-sm font-mono bg-muted p-4 rounded">
              {bodyText ?? 'No content generated yet.'}
            </pre>
          )}
          {!displayUrl && typeKey !== 'copy' && typeKey !== 'script' && (
            <p className="text-muted-foreground text-sm">Asset not yet generated.</p>
          )}
        </CardContent>
      </Card>

      {canApprove && (
        <div className="space-y-4">
          <div className="flex gap-3">
            <Button onClick={handleApprove} disabled={isPending} className="bg-green-600 hover:bg-green-700">
              Approve
            </Button>
            <Button onClick={handleReject} disabled={isPending} variant="destructive">
              Reject
            </Button>
          </div>

          <div className="space-y-2">
            <label htmlFor="revision-note" className="text-sm font-medium">Request Revision</label>
            <textarea
              id="revision-note"
              value={revisionNote}
              onChange={(e) => setRevisionNote(e.target.value)}
              placeholder="Describe the revision needed…"
              className="w-full min-h-[80px] rounded border border-input bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-ring"
            />
            <Button
              variant="outline"
              onClick={handleRequestRevision}
              disabled={isPending || !revisionNote.trim()}
            >
              Request Revision
            </Button>
          </div>
        </div>
      )}

      <Button variant="ghost" onClick={() => navigate('/creative-studio')}>
        ← Back to Studio
      </Button>
    </div>
  )
}
