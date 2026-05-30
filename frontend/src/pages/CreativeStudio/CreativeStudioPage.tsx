import { Link } from 'react-router-dom'
import { PageHeader } from '@/components/PageHeader'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useCreatives, type Creative } from '@/hooks/useCreatives'
import { Image, Music, Video, FileText, AlignLeft } from 'lucide-react'

const STATUS_BADGE: Record<NonNullable<Creative['status']>, { label: string; className: string }> = {
  ai_draft:           { label: 'AI Draft',           className: 'bg-gray-100 text-gray-700 border-gray-200' },
  internal_review:    { label: 'Internal Review',    className: 'bg-yellow-100 text-yellow-700 border-yellow-200' },
  client_review:      { label: 'Client Review',      className: 'bg-blue-100 text-blue-700 border-blue-200' },
  approved:           { label: 'Approved',            className: 'bg-green-100 text-green-700 border-green-200' },
  revision_requested: { label: 'Revision Requested', className: 'bg-orange-100 text-orange-700 border-orange-200' },
  rejected:           { label: 'Rejected',            className: 'bg-red-100 text-red-700 border-red-200' },
}

const ASSET_ICON: Record<NonNullable<Creative['asset_type']>, React.ElementType> = {
  image:  Image,
  audio:  Music,
  video:  Video,
  copy:   AlignLeft,
  script: FileText,
}

export function CreativeStudioPage() {
  const { data: creatives, isLoading, error } = useCreatives()

  if (isLoading) return <div className="p-8 text-muted-foreground">Loading assets…</div>
  if (error)    return <div className="p-8 text-destructive">Failed to load assets.</div>

  return (
    <div className="p-6 space-y-6">
      <PageHeader title="Creative Studio" description="Review and approve all campaign creative assets" />

      {(!creatives || creatives.length === 0) && (
        <p className="text-muted-foreground">No creative assets yet. Assets appear here once agents generate them.</p>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {creatives?.map((asset) => {
          // status / asset_type are optional on real backend responses (live in validation_status / creative_type)
          const statusKey = asset.status ?? (asset.validation_status as NonNullable<Creative['status']> | undefined)
          const typeKey = asset.asset_type ?? (asset.creative_type as NonNullable<Creative['asset_type']> | undefined)
          const badge = statusKey ? STATUS_BADGE[statusKey] : undefined
          const Icon = typeKey ? ASSET_ICON[typeKey] : FileText
          const displayName = asset.message_variant ?? (asset.content as Record<string,unknown> | undefined)?.['label'] as string | undefined
          const displayType = asset.asset_type ?? asset.creative_type
          const displayFormat = asset.format_spec ?? asset.platform
          const displayUrl = asset.asset_url ?? (asset.content as Record<string,unknown> | undefined)?.['url'] as string | undefined
          return (
            <Link key={asset.id} to={`/creative-studio/${asset.id}`}>
              <Card className="hover:shadow-md transition-shadow cursor-pointer">
                <CardHeader className="flex flex-row items-center gap-3 pb-2">
                  <div className="rounded-md bg-muted p-2">
                    <Icon className="h-5 w-5 text-muted-foreground" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <CardTitle className="text-sm font-medium truncate">
                      {displayName ?? asset.id}
                    </CardTitle>
                    <p className="text-xs text-muted-foreground capitalize">
                      {displayType} · {displayFormat}
                    </p>
                  </div>
                </CardHeader>
                <CardContent>
                  {displayUrl && typeKey === 'image' && (
                    <img
                      src={displayUrl}
                      alt={displayName ?? asset.id}
                      className="w-full h-32 object-cover rounded mb-3"
                    />
                  )}
                  {badge && <Badge className={badge.className}>{badge.label}</Badge>}
                  {!badge && asset.validation_status && (
                    <Badge variant="outline">{asset.validation_status}</Badge>
                  )}
                </CardContent>
              </Card>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
