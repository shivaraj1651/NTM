import { Link } from 'react-router-dom'
import { PageHeader } from '@/components/PageHeader'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardFooter } from '@/components/ui/card'
import { useCreatives, type Creative } from '@/hooks/useCreatives'
import { Image, Video, FileText, AlignLeft, ExternalLink, Tag } from 'lucide-react'

const VALIDATION_BADGE: Record<string, { label: string; className: string }> = {
  ai_draft:          { label: 'AI Draft',       className: 'bg-gray-100 text-gray-700 border-gray-200' },
  internal_approved: { label: 'Approved',        className: 'bg-green-100 text-green-700 border-green-200' },
  client_approved:   { label: 'Client OK',       className: 'bg-emerald-100 text-emerald-700 border-emerald-200' },
  revision_requested:{ label: 'Needs Revision',  className: 'bg-orange-100 text-orange-700 border-orange-200' },
}

const FORMAT_ASPECT: Record<string, string> = {
  square:        'aspect-square',
  landscape:     'aspect-video',
  portrait:      'aspect-[9/16] max-h-64',
  ooh_billboard: 'aspect-[16/5]',
}

const FORMAT_LABEL: Record<string, string> = {
  square:        'Square · 1:1',
  landscape:     'Landscape · 16:9',
  portrait:      'Story · 9:16',
  ooh_billboard: 'OOH Billboard',
}

const COPY_ICON: Record<string, React.ElementType> = {
  ooh_billboard:    Tag,
  headline:         Tag,
  social_caption:   AlignLeft,
  body_copy:        AlignLeft,
  print_ad:         FileText,
  email:            FileText,
  influencer_brief: FileText,
}

function BadgeStatus({ asset, className = '' }: { asset: Creative; className?: string }) {
  const key = asset.status ?? asset.validation_status ?? ''
  const b = VALIDATION_BADGE[key]
  if (!b) return null
  return <Badge className={`text-xs shrink-0 ${b.className} ${className}`}>{b.label}</Badge>
}

function ImageCard({ asset }: { asset: Creative }) {
  const content = asset.content as Record<string, unknown> | undefined
  const url = asset.asset_url ?? content?.['url'] as string | undefined
  const fmt = asset.platform ?? ''
  const label = content?.['label'] as string ?? FORMAT_LABEL[fmt] ?? fmt
  const tagline = content?.['tagline'] as string | undefined
  const theme = content?.['campaign_theme'] as string | undefined
  const aspectClass = FORMAT_ASPECT[fmt] ?? 'aspect-video'

  return (
    <Link to={`/creative-studio/${asset.id}`}>
      <Card className="overflow-hidden hover:shadow-lg transition-shadow cursor-pointer group border border-border">
        <div className={`relative w-full overflow-hidden bg-muted ${aspectClass}`}>
          {url ? (
            <img
              src={url}
              alt={label}
              className="absolute inset-0 w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            />
          ) : (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-gradient-to-br from-slate-800 to-slate-900">
              <Image className="h-10 w-10 text-slate-500" />
              <p className="text-xs text-slate-400">Generating…</p>
            </div>
          )}
          <div className="absolute top-2 left-2">
            <Badge className="text-xs bg-black/60 text-white border-0 backdrop-blur-sm">
              {FORMAT_LABEL[fmt] ?? fmt}
            </Badge>
          </div>
          <div className="absolute top-2 right-2">
            <BadgeStatus asset={asset} />
          </div>
          <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/80 to-transparent p-3 translate-y-full group-hover:translate-y-0 transition-transform duration-200">
            <ExternalLink className="h-4 w-4 text-white ml-auto" />
          </div>
        </div>
        <CardFooter className="py-2 px-3 flex flex-col items-start gap-0.5">
          {tagline && (
            <p className="text-sm font-semibold text-foreground italic truncate w-full">
              &ldquo;{tagline}&rdquo;
            </p>
          )}
          {theme && <p className="text-xs text-muted-foreground truncate w-full">{theme}</p>}
          {!tagline && !theme && <p className="text-sm font-medium truncate w-full">{label}</p>}
        </CardFooter>
      </Card>
    </Link>
  )
}

function CopyCard({ asset }: { asset: Creative }) {
  const content = asset.content as Record<string, unknown> | undefined
  const atype  = content?.['asset_type'] as string ?? 'copy'
  const label  = content?.['label'] as string ?? atype.replace(/_/g, ' ')
  const tagline = content?.['tagline'] as string | undefined
  const preview = content?.['preview'] as string | undefined
  const Icon = COPY_ICON[atype] ?? AlignLeft

  return (
    <Link to={`/creative-studio/${asset.id}`}>
      <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
        <CardContent className="pt-4 pb-3 space-y-2">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <div className="rounded-md bg-muted p-1.5 shrink-0">
                <Icon className="h-4 w-4 text-muted-foreground" />
              </div>
              <p className="text-sm font-semibold truncate">{label}</p>
            </div>
            <BadgeStatus asset={asset} />
          </div>
          {tagline && (
            <p className="text-xs font-medium text-primary italic line-clamp-1">
              &ldquo;{tagline}&rdquo;
            </p>
          )}
          {preview && (
            <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
              {preview}
            </p>
          )}
        </CardContent>
      </Card>
    </Link>
  )
}

function ScriptCard({ asset }: { asset: Creative }) {
  const content = asset.content as Record<string, unknown> | undefined
  const fmt     = content?.['format'] as string ?? asset.platform ?? 'script'
  const label   = content?.['label'] as string ?? fmt.replace(/_/g, ' ')
  const duration = content?.['duration_estimate'] as string | undefined
  const tagline = content?.['tagline'] as string | undefined
  const preview = content?.['content_preview'] as string | undefined

  return (
    <Link to={`/creative-studio/${asset.id}`}>
      <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
        <CardContent className="pt-4 pb-3 space-y-2">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <div className="rounded-md bg-muted p-1.5 shrink-0">
                <Video className="h-4 w-4 text-muted-foreground" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold truncate">{label}</p>
                {duration && <p className="text-xs text-muted-foreground">{duration}</p>}
              </div>
            </div>
            <BadgeStatus asset={asset} />
          </div>
          {tagline && (
            <p className="text-xs font-medium text-primary italic line-clamp-1">
              &ldquo;{tagline}&rdquo;
            </p>
          )}
          {preview && (
            <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed font-mono">
              {preview}
            </p>
          )}
        </CardContent>
      </Card>
    </Link>
  )
}

export function CreativeStudioPage() {
  const { data: creatives, isLoading, error } = useCreatives()

  if (isLoading) return <div className="p-8 text-muted-foreground">Loading assets…</div>
  if (error)    return <div className="p-8 text-destructive">Failed to load assets.</div>

  const images  = creatives?.filter(a => (a.creative_type ?? a.asset_type) === 'image')  ?? []
  const copies  = creatives?.filter(a => (a.creative_type ?? a.asset_type) === 'copy')   ?? []
  const scripts = creatives?.filter(a => (a.creative_type ?? a.asset_type) === 'script') ?? []
  const others  = creatives?.filter(a => {
    const t = a.creative_type ?? a.asset_type
    return t !== 'image' && t !== 'copy' && t !== 'script'
  }) ?? []

  if (!creatives || creatives.length === 0) {
    return (
      <div className="p-6 space-y-6">
        <PageHeader title="Creative Studio" description="Review and approve all campaign creative assets" />
        <p className="text-muted-foreground">
          No creative assets yet. Generate creatives from an approved campaign to see them here.
        </p>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-10">
      <PageHeader title="Creative Studio" description="Review and approve all campaign creative assets" />

      {/* Visual Ads — images rendered at proper ad aspect ratios */}
      {images.length > 0 && (
        <section className="space-y-4">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
            Visual Ads ({images.length})
          </h2>
          <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
            {images.map(a => <ImageCard key={a.id} asset={a} />)}
          </div>
        </section>
      )}

      {/* Copy Assets */}
      {copies.length > 0 && (
        <section className="space-y-4">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
            Copy Assets ({copies.length})
          </h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {copies.map(a => <CopyCard key={a.id} asset={a} />)}
          </div>
        </section>
      )}

      {/* Scripts */}
      {scripts.length > 0 && (
        <section className="space-y-4">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
            Scripts ({scripts.length})
          </h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {scripts.map(a => <ScriptCard key={a.id} asset={a} />)}
          </div>
        </section>
      )}

      {/* Other (audio, video, etc.) */}
      {others.length > 0 && (
        <section className="space-y-4">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
            Other Assets ({others.length})
          </h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {others.map(a => {
              const content = a.content as Record<string,unknown> | undefined
              const label = a.message_variant ?? content?.['label'] as string ?? a.id
              const typeKey = a.creative_type ?? a.asset_type
              return (
                <Link key={a.id} to={`/creative-studio/${a.id}`}>
                  <Card className="hover:shadow-md transition-shadow cursor-pointer">
                    <CardContent className="pt-4 pb-3 flex items-center gap-3">
                      <div className="rounded-md bg-muted p-1.5 shrink-0">
                        <FileText className="h-4 w-4 text-muted-foreground" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{label}</p>
                        <p className="text-xs text-muted-foreground capitalize">{typeKey} · {a.platform}</p>
                      </div>
                      <BadgeStatus asset={a} />
                    </CardContent>
                  </Card>
                </Link>
              )
            })}
          </div>
        </section>
      )}
    </div>
  )
}
