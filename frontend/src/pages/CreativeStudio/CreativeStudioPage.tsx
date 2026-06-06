import { Link } from 'react-router-dom'
import { PageHeader } from '@/components/PageHeader'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardFooter } from '@/components/ui/card'
import { useCreatives, useRegenerateCreative, useDownloadCreative, type Creative } from '@/hooks/useCreatives'
import { Image, Video, FileText, AlignLeft, ExternalLink, Tag, Newspaper, Link2, Monitor, RefreshCw, Download } from 'lucide-react'

// ── constants ──────────────────────────────────────────────────────────────

const VALIDATION_BADGE: Record<string, { label: string; className: string }> = {
  ai_draft:           { label: 'AI Draft',      className: 'bg-gray-100 text-gray-700 border-gray-200' },
  internal_approved:  { label: 'Approved',       className: 'bg-green-100 text-green-700 border-green-200' },
  client_approved:    { label: 'Client OK',      className: 'bg-emerald-100 text-emerald-700 border-emerald-200' },
  revision_requested: { label: 'Needs Revision', className: 'bg-orange-100 text-orange-700 border-orange-200' },
}

// Maps image platform → CSS aspect ratio and display label
const FORMAT_META: Record<string, { aspect: string; label: string }> = {
  square:           { aspect: 'aspect-square',    label: 'Square · 1:1' },
  landscape:        { aspect: 'aspect-video',      label: 'Landscape · 16:9' },
  portrait:         { aspect: 'aspect-[9/16]',     label: 'Story · 9:16' },
  ooh_billboard:    { aspect: 'aspect-[16/5]',     label: 'OOH Billboard' },
  newspaper_insert: { aspect: 'aspect-[3/4]',      label: 'Newspaper Insert' },
  linkedin_post:    { aspect: 'aspect-square',     label: 'LinkedIn Post' },
}

const COPY_ICON: Record<string, React.ElementType> = {
  ooh_billboard:    Tag,
  headline:         Tag,
  social_caption:   AlignLeft,
  body_copy:        AlignLeft,
  print_ad:         Newspaper,
  email:            FileText,
  influencer_brief: FileText,
  linkedin_post:    Link2,
}

// Maps copy asset_type → which creative tab it belongs to
const COPY_SECTION: Record<string, string> = {
  ooh_billboard:    'ooh',
  print_ad:         'newspaper',
  linkedin_post:    'linkedin',
  social_caption:   'ads',
  headline:         'ads',
  body_copy:        'ads',
  email:            'ads',
  influencer_brief: 'ads',
}

// Maps image platform → which creative section it belongs to
const IMAGE_SECTION: Record<string, string> = {
  ooh_billboard:    'ooh',
  newspaper_insert: 'newspaper',
  linkedin_post:    'linkedin',
  square:           'ads',
  landscape:        'ads',
  portrait:         'ads',
}

// ── card components ────────────────────────────────────────────────────────

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
  const meta = FORMAT_META[fmt]
  const label = content?.['label'] as string ?? meta?.label ?? fmt
  const tagline = content?.['tagline'] as string | undefined
  const theme = content?.['campaign_theme'] as string | undefined

  const regenerate = useRegenerateCreative()
  const download = useDownloadCreative()

  function handleRegenerate(e: React.MouseEvent) {
    e.preventDefault(); e.stopPropagation()
    regenerate.mutate({ campaignId: asset.campaign_id, assetKind: asset.creative_type ?? 'image', assetId: asset.id })
  }

  function handleDownload(e: React.MouseEvent) {
    e.preventDefault(); e.stopPropagation()
    if (url) { window.open(url, '_blank') }
    else { download.mutate(asset.id, { onSuccess: (d) => window.open(d.asset_url, '_blank') }) }
  }

  return (
    <Link to={`/creative-studio/${asset.id}`}>
      <Card className="overflow-hidden hover:shadow-lg transition-shadow cursor-pointer group border border-border">
        <div className={`relative w-full overflow-hidden bg-muted ${meta?.aspect ?? 'aspect-video'}`}>
          {url ? (
            <img src={url} alt={label}
              className="absolute inset-0 w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
          ) : (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-gradient-to-br from-slate-800 to-slate-900">
              <Image className="h-10 w-10 text-slate-500" />
              <p className="text-xs text-slate-400">Generating…</p>
            </div>
          )}
          <div className="absolute top-2 left-2">
            <Badge className="text-xs bg-black/60 text-white border-0 backdrop-blur-sm">{label}</Badge>
          </div>
          <div className="absolute top-2 right-2"><BadgeStatus asset={asset} /></div>
          <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/80 to-transparent p-3 translate-y-full group-hover:translate-y-0 transition-transform duration-200">
            <ExternalLink className="h-4 w-4 text-white ml-auto" />
          </div>
        </div>
        <CardFooter className="py-2 px-3 flex items-center justify-between gap-1">
          <div className="flex flex-col items-start gap-0.5 min-w-0 flex-1">
            {tagline && <p className="text-sm font-semibold text-foreground italic truncate w-full">&ldquo;{tagline}&rdquo;</p>}
            {theme && <p className="text-xs text-muted-foreground truncate w-full">{theme}</p>}
            {!tagline && !theme && <p className="text-sm font-medium truncate w-full">{label}</p>}
          </div>
          <div className="flex gap-1 shrink-0">
            <Button size="icon" variant="ghost" className="h-7 w-7" title="Regenerate"
              disabled={regenerate.isPending} onClick={handleRegenerate}>
              <RefreshCw className={`h-3.5 w-3.5 ${regenerate.isPending ? 'animate-spin' : ''}`} />
            </Button>
            <Button size="icon" variant="ghost" className="h-7 w-7" title="Download"
              disabled={download.isPending} onClick={handleDownload}>
              <Download className="h-3.5 w-3.5" />
            </Button>
          </div>
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

  const regenerate = useRegenerateCreative()

  function handleRegenerate(e: React.MouseEvent) {
    e.preventDefault(); e.stopPropagation()
    regenerate.mutate({ campaignId: asset.campaign_id, assetKind: asset.creative_type ?? 'copy', assetId: asset.id })
  }

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
            <div className="flex items-center gap-1 shrink-0">
              <BadgeStatus asset={asset} />
              <Button size="icon" variant="ghost" className="h-7 w-7" title="Regenerate"
                disabled={regenerate.isPending} onClick={handleRegenerate}>
                <RefreshCw className={`h-3.5 w-3.5 ${regenerate.isPending ? 'animate-spin' : ''}`} />
              </Button>
            </div>
          </div>
          {tagline && <p className="text-xs font-medium text-primary italic line-clamp-1">&ldquo;{tagline}&rdquo;</p>}
          {preview && <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">{preview}</p>}
        </CardContent>
      </Card>
    </Link>
  )
}

function VideoCard({ asset }: { asset: Creative }) {
  const content = asset.content as Record<string, unknown> | undefined
  const url = asset.asset_url ?? content?.['url'] as string | undefined
  const status = (content?.['status'] as string | undefined) ?? asset.status

  const regenerate = useRegenerateCreative()
  const download = useDownloadCreative()

  function handleRegenerate(e: React.MouseEvent) {
    e.preventDefault(); e.stopPropagation()
    regenerate.mutate({ campaignId: asset.campaign_id, assetKind: asset.creative_type ?? 'video', assetId: asset.id })
  }

  function handleDownload(e: React.MouseEvent) {
    e.preventDefault(); e.stopPropagation()
    if (url) { window.open(url, '_blank') }
    else { download.mutate(asset.id, { onSuccess: (d) => window.open(d.asset_url, '_blank') }) }
  }

  return (
    <Link to={`/creative-studio/${asset.id}`}>
      <Card className="overflow-hidden hover:shadow-lg transition-shadow cursor-pointer group border border-border">
        <div className="relative w-full overflow-hidden bg-muted aspect-video">
          {url ? (
            /* eslint-disable-next-line jsx-a11y/media-has-caption */
            <video src={url} className="absolute inset-0 w-full h-full object-cover" />
          ) : (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-gradient-to-br from-slate-800 to-slate-900">
              <Video className="h-10 w-10 text-slate-500" />
              <p className="text-xs text-slate-400">
                {status === 'manual_production_required' ? 'Manual production required' : 'Generating…'}
              </p>
            </div>
          )}
          <div className="absolute top-2 left-2">
            <Badge className="text-xs bg-black/60 text-white border-0 backdrop-blur-sm">Reel / Short Ad</Badge>
          </div>
          <div className="absolute top-2 right-2"><BadgeStatus asset={asset} /></div>
        </div>
        <CardFooter className="py-2 px-3 flex items-center justify-between">
          <p className="text-sm font-medium">Video Ad</p>
          <div className="flex gap-1">
            <Button size="icon" variant="ghost" className="h-7 w-7" title="Regenerate"
              disabled={regenerate.isPending} onClick={handleRegenerate}>
              <RefreshCw className={`h-3.5 w-3.5 ${regenerate.isPending ? 'animate-spin' : ''}`} />
            </Button>
            <Button size="icon" variant="ghost" className="h-7 w-7" title="Download"
              disabled={download.isPending} onClick={handleDownload}>
              <Download className="h-3.5 w-3.5" />
            </Button>
          </div>
        </CardFooter>
      </Card>
    </Link>
  )
}

// ── section component ──────────────────────────────────────────────────────

function Section({
  icon: Icon, title, count, children,
}: {
  icon: React.ElementType
  title: string
  count: number
  children: React.ReactNode
}) {
  if (count === 0) return null
  return (
    <section className="space-y-4">
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 text-muted-foreground" />
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
          {title} ({count})
        </h2>
      </div>
      {children}
    </section>
  )
}

// ── page ───────────────────────────────────────────────────────────────────

export function CreativeStudioPage() {
  const { data: creatives, isLoading, error } = useCreatives()

  if (isLoading) return <div className="p-8 text-muted-foreground">Loading assets…</div>
  if (error)    return <div className="p-8 text-destructive">Failed to load assets.</div>

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

  const byType = (type: string) =>
    creatives.filter(a => (a.creative_type ?? a.asset_type) === type)

  const videos    = byType('video')
  const allImages = byType('image')
  const allCopy   = byType('copy')

  // Partition images by section
  const oohImages       = allImages.filter(a => IMAGE_SECTION[a.platform ?? ''] === 'ooh')
  const newspaperImages = allImages.filter(a => IMAGE_SECTION[a.platform ?? ''] === 'newspaper')
  const linkedinImages  = allImages.filter(a => IMAGE_SECTION[a.platform ?? ''] === 'linkedin')
  const adImages        = allImages.filter(a => IMAGE_SECTION[a.platform ?? ''] === 'ads')

  // Partition copy by section
  const oohCopy       = allCopy.filter(a => COPY_SECTION[(a.content as Record<string,unknown>)?.['asset_type'] as string] === 'ooh')
  const newspaperCopy = allCopy.filter(a => COPY_SECTION[(a.content as Record<string,unknown>)?.['asset_type'] as string] === 'newspaper')
  const linkedinCopy  = allCopy.filter(a => COPY_SECTION[(a.content as Record<string,unknown>)?.['asset_type'] as string] === 'linkedin')
  const adsCopy       = allCopy.filter(a => COPY_SECTION[(a.content as Record<string,unknown>)?.['asset_type'] as string] === 'ads')

  return (
    <div className="p-6 space-y-10">
      <PageHeader title="Creative Studio" description="Review and approve all campaign creative assets" />

      {/* 1 — Video */}
      <Section icon={Video} title="Video — Reel / Short Ad" count={videos.length}>
        <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {videos.map(a => <VideoCard key={a.id} asset={a} />)}
        </div>
      </Section>

      {/* 2 — OOH Billboard */}
      <Section icon={Monitor} title="OOH Billboard" count={oohImages.length + oohCopy.length}>
        {oohImages.length > 0 && (
          <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
            {oohImages.map(a => <ImageCard key={a.id} asset={a} />)}
          </div>
        )}
        {oohCopy.length > 0 && (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {oohCopy.map(a => <CopyCard key={a.id} asset={a} />)}
          </div>
        )}
      </Section>

      {/* 3 — Newspaper Insert */}
      <Section icon={Newspaper} title="Newspaper Insert / Print" count={newspaperImages.length + newspaperCopy.length}>
        {newspaperImages.length > 0 && (
          <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
            {newspaperImages.map(a => <ImageCard key={a.id} asset={a} />)}
          </div>
        )}
        {newspaperCopy.length > 0 && (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {newspaperCopy.map(a => <CopyCard key={a.id} asset={a} />)}
          </div>
        )}
      </Section>

      {/* 4 — LinkedIn Post */}
      <Section icon={Link2} title="LinkedIn Post / Content" count={linkedinImages.length + linkedinCopy.length}>
        {linkedinImages.length > 0 && (
          <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
            {linkedinImages.map(a => <ImageCard key={a.id} asset={a} />)}
          </div>
        )}
        {linkedinCopy.length > 0 && (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {linkedinCopy.map(a => <CopyCard key={a.id} asset={a} />)}
          </div>
        )}
      </Section>

      {/* 5 — Ad Images */}
      <Section icon={Image} title="Ad Images" count={adImages.length + adsCopy.length}>
        {adImages.length > 0 && (
          <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
            {adImages.map(a => <ImageCard key={a.id} asset={a} />)}
          </div>
        )}
        {adsCopy.length > 0 && (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {adsCopy.map(a => <CopyCard key={a.id} asset={a} />)}
          </div>
        )}
      </Section>
    </div>
  )
}
