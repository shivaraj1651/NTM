import { useParams, useNavigate } from 'react-router-dom'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Check, X, Copy, Download, RefreshCw, Loader2, Newspaper, Linkedin, Image, Video, Monitor } from 'lucide-react'
import {
  useCampaign,
  useGenerateCreatives,
  useApproveCreativeAsset,
  useRegenerateAsset,
} from '@/hooks/useCampaigns'
import type { ApproveAssetPayload, RegeneratePayload } from '@/hooks/useCampaigns'
import type { CopyAsset, ImageAsset, AudioAsset, VideoAsset } from '@/types/admin'

// ── helpers ────────────────────────────────────────────────────────────────

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

function ApproveButtons({
  approved, onApprove, onReject, disabled,
}: {
  approved: boolean | null
  onApprove: () => void
  onReject: () => void
  disabled?: boolean
}) {
  return (
    <div className="flex gap-1">
      <Button
        variant={approved === true ? 'default' : 'outline'} size="sm"
        className={approved === true ? 'bg-green-600 hover:bg-green-700 text-white' : ''}
        onClick={onApprove} disabled={disabled}
      >
        <Check className="h-3 w-3" />
      </Button>
      <Button
        variant={approved === false ? 'default' : 'outline'} size="sm"
        className={approved === false ? 'bg-red-600 hover:bg-red-700 text-white' : ''}
        onClick={onReject} disabled={disabled}
      >
        <X className="h-3 w-3" />
      </Button>
    </div>
  )
}

// ── copy helper ────────────────────────────────────────────────────────────

function copyText(asset: CopyAsset | undefined): string {
  if (!asset) return ''
  const v = asset.variants[0]
  if (!v) return ''
  const c = v.content
  if (typeof c === 'string') return c
  return (c as Record<string, unknown>)?.text as string ?? JSON.stringify(c)
}

function CopyBlock({ asset, onApprove, onRegenerate, isPending, assetKind }: {
  asset: CopyAsset
  onApprove: (p: ApproveAssetPayload) => void
  onRegenerate: (p: RegeneratePayload) => void
  isPending?: boolean
  assetKind: string
}) {
  return (
    <div className="space-y-2 bg-muted/30 rounded-lg p-4">
      {asset.variants.map((v) => {
        const text = typeof v.content === 'string'
          ? v.content
          : (v.content as Record<string, unknown>)?.text as string ?? JSON.stringify(v.content)
        return (
          <p key={v.variant_id ?? v.variant} className="text-sm whitespace-pre-wrap leading-relaxed">{text}</p>
        )
      })}
      <div className="flex items-center gap-2 pt-2">
        <ApproveButtons
          approved={asset.approved}
          onApprove={() => onApprove({ assetKind: assetKind as 'copy', assetId: asset.asset_type, approved: true })}
          onReject={() => onApprove({ assetKind: assetKind as 'copy', assetId: asset.asset_type, approved: false })}
          disabled={isPending}
        />
        <Button variant="ghost" size="sm" className="gap-1 text-xs px-2"
          onClick={() => navigator.clipboard.writeText(copyText(asset))}>
          <Copy className="h-3 w-3" /> Copy
        </Button>
        <Button variant="outline" size="sm" className="gap-1 text-xs"
          onClick={() => onRegenerate({ assetKind: 'copy', assetId: asset.asset_type })}
          disabled={isPending}>
          <RefreshCw className="h-3 w-3" /> Regenerate
        </Button>
      </div>
    </div>
  )
}

// ── image helper ───────────────────────────────────────────────────────────

function ImageCard({ img, aspectStyle, label, onApprove, onRegenerate, isPending }: {
  img: ImageAsset
  aspectStyle: React.CSSProperties
  label: string
  onApprove: (p: ApproveAssetPayload) => void
  onRegenerate: (p: RegeneratePayload) => void
  isPending?: boolean
}) {
  return (
    <Card>
      <CardContent className="pt-4 space-y-2">
        <img src={img.url} alt={label} className="w-full rounded object-cover" style={aspectStyle} />
        <div className="flex items-center justify-between">
          <Badge variant="outline" className="text-xs">{label}</Badge>
          {img.approved === true && <Badge className="bg-green-600 text-white text-xs">Approved</Badge>}
          {img.approved === false && <Badge variant="destructive" className="text-xs">Rejected</Badge>}
        </div>
        <div className="flex items-center gap-1 flex-wrap">
          <ApproveButtons
            approved={img.approved}
            onApprove={() => onApprove({ assetKind: 'images', assetId: img.id, approved: true })}
            onReject={() => onApprove({ assetKind: 'images', assetId: img.id, approved: false })}
            disabled={isPending}
          />
          <Button asChild variant="ghost" size="sm" className="gap-1 text-xs px-2">
            <a href={img.url} download><Download className="h-3 w-3" /> Download</a>
          </Button>
          <Button variant="outline" size="sm" className="gap-1 text-xs"
            onClick={() => onRegenerate({ assetKind: 'images', assetId: img.id })}
            disabled={isPending}>
            <RefreshCw className="h-3 w-3" /> Regenerate
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

// ── tab components ─────────────────────────────────────────────────────────

function VideoCreativesTab({ assets }: { assets: VideoAsset[] }) {
  if (assets.length === 0) {
    return (
      <div className="py-12 text-center space-y-2">
        <Video className="h-10 w-10 text-muted-foreground mx-auto" />
        <p className="text-sm text-muted-foreground">No video generated yet. Video runs after creatives are created.</p>
      </div>
    )
  }
  return (
    <div className="grid grid-cols-2 gap-4">
      {assets.map((vid) => (
        <Card key={vid.id}>
          <CardContent className="pt-4 space-y-2">
            {vid.url ? (
              /* eslint-disable-next-line jsx-a11y/media-has-caption */
              <video controls src={vid.url} className="w-full rounded" style={{ aspectRatio: '16/9' }} />
            ) : (
              <div className="w-full rounded bg-muted flex flex-col items-center justify-center gap-2 text-xs text-muted-foreground" style={{ aspectRatio: '16/9' }}>
                <Video className="h-6 w-6" />
                {vid.status === 'manual_production_required' ? 'Manual production required' : 'Generating…'}
              </div>
            )}
            <div className="flex items-center justify-between">
              <Badge variant="outline" className="text-xs">Reel / Short Ad</Badge>
              {vid.duration_seconds != null && (
                <span className="text-xs text-muted-foreground">{formatDuration(vid.duration_seconds)}</span>
              )}
            </div>
            {vid.url && (
              <Button asChild variant="ghost" size="sm" className="gap-1 text-xs px-2">
                <a href={vid.url} download><Download className="h-3 w-3" /> Download</a>
              </Button>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

function OOHBillboardTab({
  images, copy, onApprove, onRegenerate, isPending,
}: {
  images: ImageAsset[]
  copy: CopyAsset | undefined
  onApprove: (p: ApproveAssetPayload) => void
  onRegenerate: (p: RegeneratePayload) => void
  isPending?: boolean
}) {
  const billboard = images.find(i => i.format === 'ooh_billboard')
  return (
    <div className="space-y-6">
      {billboard ? (
        <ImageCard img={billboard} aspectStyle={{ aspectRatio: '16/5' }} label="OOH Billboard (1536×1024)"
          onApprove={onApprove} onRegenerate={onRegenerate} isPending={isPending} />
      ) : (
        <div className="rounded-lg bg-muted flex items-center justify-center text-sm text-muted-foreground" style={{ aspectRatio: '16/5' }}>
          <Monitor className="h-6 w-6 mr-2" /> No billboard image generated
        </div>
      )}
      {copy && (
        <div className="space-y-2">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Billboard Copy</p>
          <CopyBlock asset={copy} onApprove={onApprove} onRegenerate={onRegenerate} isPending={isPending} assetKind="copy" />
        </div>
      )}
    </div>
  )
}

function NewspaperInsertTab({
  images, copy, onApprove, onRegenerate, isPending,
}: {
  images: ImageAsset[]
  copy: CopyAsset | undefined
  onApprove: (p: ApproveAssetPayload) => void
  onRegenerate: (p: RegeneratePayload) => void
  isPending?: boolean
}) {
  const insert = images.find(i => i.format === 'newspaper_insert')
  return (
    <div className="grid grid-cols-2 gap-6 items-start">
      <div>
        {insert ? (
          <ImageCard img={insert} aspectStyle={{ aspectRatio: '3/4' }} label="Newspaper Insert (1024×1536)"
            onApprove={onApprove} onRegenerate={onRegenerate} isPending={isPending} />
        ) : (
          <div className="rounded-lg bg-muted flex flex-col items-center justify-center gap-2 text-sm text-muted-foreground" style={{ aspectRatio: '3/4' }}>
            <Newspaper className="h-8 w-8" /> No newspaper insert generated
          </div>
        )}
      </div>
      <div className="space-y-2">
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Print Ad Copy</p>
        {copy ? (
          <CopyBlock asset={copy} onApprove={onApprove} onRegenerate={onRegenerate} isPending={isPending} assetKind="copy" />
        ) : (
          <p className="text-sm text-muted-foreground">No print copy generated.</p>
        )}
      </div>
    </div>
  )
}

function LinkedInTab({
  images, copy, audio, onApprove, onRegenerate, isPending,
}: {
  images: ImageAsset[]
  copy: CopyAsset | undefined
  audio: AudioAsset[]
  onApprove: (p: ApproveAssetPayload) => void
  onRegenerate: (p: RegeneratePayload) => void
  isPending?: boolean
}) {
  const liImg = images.find(i => i.format === 'linkedin_post')
  const voiceover = audio[0]
  return (
    <div className="grid grid-cols-2 gap-6 items-start">
      <div>
        {liImg ? (
          <ImageCard img={liImg} aspectStyle={{ aspectRatio: '1/1' }} label="LinkedIn Post (1024×1024)"
            onApprove={onApprove} onRegenerate={onRegenerate} isPending={isPending} />
        ) : (
          <div className="rounded-lg bg-muted flex flex-col items-center justify-center gap-2 text-sm text-muted-foreground" style={{ aspectRatio: '1/1' }}>
            <Linkedin className="h-8 w-8" /> No LinkedIn image generated
          </div>
        )}
      </div>
      <div className="space-y-4">
        {copy && (
          <div className="space-y-2">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">LinkedIn Post Copy</p>
            <CopyBlock asset={copy} onApprove={onApprove} onRegenerate={onRegenerate} isPending={isPending} assetKind="copy" />
          </div>
        )}
        {voiceover && (
          <div className="space-y-2">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Voiceover</p>
            {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
            {voiceover.url && <audio controls src={voiceover.url} className="w-full" />}
          </div>
        )}
      </div>
    </div>
  )
}

function AdImagesTab({
  images, copy, onApprove, onRegenerate, isPending,
}: {
  images: ImageAsset[]
  copy: CopyAsset | undefined
  onApprove: (p: ApproveAssetPayload) => void
  onRegenerate: (p: RegeneratePayload) => void
  isPending?: boolean
}) {
  const adFormats: Array<{ format: ImageAsset['format']; label: string; style: React.CSSProperties }> = [
    { format: 'square',    label: 'Square · 1:1',    style: { aspectRatio: '1/1' } },
    { format: 'landscape', label: 'Landscape · 16:9', style: { aspectRatio: '16/9' } },
    { format: 'portrait',  label: 'Story · 9:16',    style: { aspectRatio: '9/16', maxHeight: '320px' } },
  ]
  const caption = copy
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-4">
        {adFormats.map(({ format, label, style }) => {
          const img = images.find(i => i.format === format)
          return img ? (
            <ImageCard key={format} img={img} aspectStyle={style} label={label}
              onApprove={onApprove} onRegenerate={onRegenerate} isPending={isPending} />
          ) : (
            <div key={format} className="rounded-lg bg-muted flex flex-col items-center justify-center gap-2 text-xs text-muted-foreground" style={style}>
              <Image className="h-6 w-6" /> {label}
            </div>
          )
        })}
      </div>
      {caption && (
        <div className="space-y-2">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Social Caption</p>
          <CopyBlock asset={caption} onApprove={onApprove} onRegenerate={onRegenerate} isPending={isPending} assetKind="copy" />
        </div>
      )}
    </div>
  )
}

// ── main page ──────────────────────────────────────────────────────────────

export function CreativesPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: campaign, isError } = useCampaign(id ?? '')
  const generateCreatives = useGenerateCreatives(id ?? '')
  const approveAsset = useApproveCreativeAsset(id ?? '')
  const regenerateAsset = useRegenerateAsset(id ?? '')

  if (!id) return null
  if (isError) return <p className="text-destructive text-sm">Failed to load campaign.</p>
  if (!campaign) return null

  const { status, creative_assets } = campaign

  if (status === 'approved') {
    return (
      <div className="space-y-4">
        <div>
          <h2 className="text-lg font-semibold">Creative Assets</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Generate video, billboard, newspaper insert, LinkedIn post, and ad images for this campaign.
          </p>
        </div>
        {generateCreatives.isError && (
          <p className="text-destructive text-sm">Generation failed. Please try again.</p>
        )}
        {generateCreatives.isPending ? (
          <div className="flex items-center gap-2 text-muted-foreground text-sm">
            <Loader2 className="h-4 w-4 animate-spin" />
            Generating assets…
          </div>
        ) : (
          <Button onClick={() => generateCreatives.mutate()}>Generate Creatives</Button>
        )}
      </div>
    )
  }

  if (campaign?.status === 'creative_generating') {
    return (
      <div className="flex items-center gap-2 text-muted-foreground text-sm py-8">
        <Loader2 className="h-4 w-4 animate-spin" />
        Generating all 5 creative types… this may take a few minutes.
      </div>
    )
  }

  const CREATIVE_STAGES = ['creative_ready', 'live']
  if (!CREATIVE_STAGES.includes(status) || !creative_assets) {
    return <p className="text-muted-foreground text-sm">No assets available.</p>
  }

  const { images = [], copy = [], audio = [], video = [] } = creative_assets

  const getCopy = (type: string) => copy.find(c => c.asset_type === type)
  const sharedProps = { onApprove: approveAsset.mutate, onRegenerate: regenerateAsset.mutate, isPending: approveAsset.isPending || regenerateAsset.isPending }

  return (
    <div>
      <h2 className="text-lg font-semibold mb-4">Creative Assets</h2>
      <Tabs defaultValue="video">
        <TabsList className="flex gap-1 flex-wrap h-auto">
          <TabsTrigger value="video" className="gap-1.5"><Video className="h-3.5 w-3.5" /> Video</TabsTrigger>
          <TabsTrigger value="ooh" className="gap-1.5"><Monitor className="h-3.5 w-3.5" /> OOH Billboard</TabsTrigger>
          <TabsTrigger value="newspaper" className="gap-1.5"><Newspaper className="h-3.5 w-3.5" /> Newspaper Insert</TabsTrigger>
          <TabsTrigger value="linkedin" className="gap-1.5"><Linkedin className="h-3.5 w-3.5" /> LinkedIn Post</TabsTrigger>
          <TabsTrigger value="ads" className="gap-1.5"><Image className="h-3.5 w-3.5" /> Ad Images</TabsTrigger>
        </TabsList>

        <TabsContent value="video" className="mt-4">
          <VideoCreativesTab assets={video} />
        </TabsContent>

        <TabsContent value="ooh" className="mt-4">
          <OOHBillboardTab images={images} copy={getCopy('ooh_billboard')} {...sharedProps} />
        </TabsContent>

        <TabsContent value="newspaper" className="mt-4">
          <NewspaperInsertTab images={images} copy={getCopy('print_ad')} {...sharedProps} />
        </TabsContent>

        <TabsContent value="linkedin" className="mt-4">
          <LinkedInTab images={images} copy={getCopy('linkedin_post')} audio={audio} {...sharedProps} />
        </TabsContent>

        <TabsContent value="ads" className="mt-4">
          <AdImagesTab images={images} copy={getCopy('social_caption')} {...sharedProps} />
        </TabsContent>
      </Tabs>

      {status === 'creative_ready' && (
        <div className="mt-6">
          <Button onClick={() => navigate(`/campaigns/${id}/go-live`)}>
            Proceed to Go Live →
          </Button>
        </div>
      )}
    </div>
  )
}
