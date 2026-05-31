import { useParams, useNavigate } from 'react-router-dom'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Check, X, Copy, Download, RefreshCw, Loader2 } from 'lucide-react'
import {
  useCampaign,
  useGenerateCreatives,
  useApproveCreativeAsset,
  useRegenerateAsset,
} from '@/hooks/useCampaigns'
import type { ApproveAssetPayload, RegeneratePayload } from '@/hooks/useCampaigns'
import type { CopyAsset, CopyAssetType, ScriptAsset, ImageAsset, AudioAsset } from '@/types/admin'

const COPY_ASSET_LABELS: Record<CopyAssetType, string> = {
  social_caption: 'Social Caption',
  headline: 'Headline',
  body_copy: 'Body Copy',
  print_ad: 'Print Ad',
  email: 'Email',
  ooh_billboard: 'OOH Billboard',
  influencer_brief: 'Influencer Brief',
}

const MEDIA_FORMAT_LABELS: Record<string, string> = {
  tvc_vo: 'TVC Voiceover',
  radio: 'Radio',
  social_video: 'Social Video',
}

const VOICE_LABELS: Record<string, string> = {
  warm: 'Warm',
  authoritative: 'Authoritative',
  youthful: 'Youthful',
}

const IMAGE_FORMAT_LABELS: Record<string, string> = {
  square: 'Square (1024×1024)',
  landscape: 'Landscape (1344×768)',
  portrait: 'Portrait (768×1344)',
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

function ApproveButtons({
  approved,
  onApprove,
  onReject,
  disabled,
}: {
  approved: boolean | null
  onApprove: () => void
  onReject: () => void
  disabled?: boolean
}) {
  return (
    <div className="flex gap-1">
      <Button
        variant={approved === true ? 'default' : 'outline'}
        size="sm"
        className={approved === true ? 'bg-green-600 hover:bg-green-700 text-white' : ''}
        onClick={onApprove}
        disabled={disabled}
      >
        <Check className="h-3 w-3" />
      </Button>
      <Button
        variant={approved === false ? 'default' : 'outline'}
        size="sm"
        className={approved === false ? 'bg-red-600 hover:bg-red-700 text-white' : ''}
        onClick={onReject}
        disabled={disabled}
      >
        <X className="h-3 w-3" />
      </Button>
    </div>
  )
}

function CopyTab({
  assets,
  onApprove,
  onRegenerate,
  isPending,
}: {
  assets: CopyAsset[]
  onApprove: (p: ApproveAssetPayload) => void
  onRegenerate: (p: RegeneratePayload) => void
  isPending?: boolean
}) {
  return (
    <Accordion type="single" collapsible className="w-full">
      {assets.map((asset) => (
        <AccordionItem key={asset.asset_type} value={asset.asset_type}>
          <AccordionTrigger className="hover:no-underline">
            <div className="flex items-center gap-3">
              <span className="font-medium">{COPY_ASSET_LABELS[asset.asset_type]}</span>
              {asset.approved === true && (
                <Badge className="bg-green-600 text-white text-xs">Approved</Badge>
              )}
              {asset.approved === false && (
                <Badge variant="destructive" className="text-xs">Rejected</Badge>
              )}
            </div>
          </AccordionTrigger>
          <AccordionContent>
            <div className="space-y-3 pt-2">
              <div className="grid grid-cols-2 gap-4">
                {asset.variants.map((v) => (
                  <Card key={v.variant}>
                    <CardContent className="pt-4 space-y-2">
                      <div className="flex items-center justify-between">
                        <Badge variant="outline">Variant {v.variant}</Badge>
                        <Badge variant="secondary" className="text-xs">{v.word_count} words</Badge>
                      </div>
                      <p className="text-sm whitespace-pre-wrap max-h-40 overflow-y-auto leading-relaxed">
                        {v.content}
                      </p>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="gap-1 text-xs px-2"
                        onClick={() => navigator.clipboard.writeText(v.content)}
                      >
                        <Copy className="h-3 w-3" /> Copy
                      </Button>
                    </CardContent>
                  </Card>
                ))}
              </div>
              <div className="flex items-center gap-2 pt-1">
                <ApproveButtons
                  approved={asset.approved}
                  onApprove={() =>
                    onApprove({ assetKind: 'copy', assetId: asset.asset_type, approved: true })
                  }
                  onReject={() =>
                    onApprove({ assetKind: 'copy', assetId: asset.asset_type, approved: false })
                  }
                  disabled={isPending}
                />
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1 text-xs"
                  onClick={() => onRegenerate({ assetKind: 'copy', assetId: asset.asset_type })}
                  disabled={isPending}
                >
                  <RefreshCw className="h-3 w-3" /> Regenerate
                </Button>
              </div>
            </div>
          </AccordionContent>
        </AccordionItem>
      ))}
    </Accordion>
  )
}

function ScriptsTab({
  assets,
  onApprove,
  onRegenerate,
  isPending,
}: {
  assets: ScriptAsset[]
  onApprove: (p: ApproveAssetPayload) => void
  onRegenerate: (p: RegeneratePayload) => void
  isPending?: boolean
}) {
  return (
    <div className="space-y-4">
      {assets.map((script) => (
        <Card key={script.id}>
          <CardContent className="pt-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex gap-2">
                <Badge variant="outline">
                  {MEDIA_FORMAT_LABELS[script.format] ?? script.format}
                </Badge>
                <Badge variant="secondary" className="text-xs">{script.duration_estimate}</Badge>
              </div>
              {script.approved === true && (
                <Badge className="bg-green-600 text-white text-xs">Approved</Badge>
              )}
              {script.approved === false && (
                <Badge variant="destructive" className="text-xs">Rejected</Badge>
              )}
            </div>
            <pre className="text-sm whitespace-pre-wrap bg-muted/30 rounded p-3 max-h-48 overflow-y-auto font-sans leading-relaxed">
              {script.content}
            </pre>
            <div className="flex items-center gap-2">
              <ApproveButtons
                approved={script.approved}
                onApprove={() =>
                  onApprove({ assetKind: 'scripts', assetId: script.id, approved: true })
                }
                onReject={() =>
                  onApprove({ assetKind: 'scripts', assetId: script.id, approved: false })
                }
                disabled={isPending}
              />
              <Button
                variant="ghost"
                size="sm"
                className="gap-1 text-xs"
                onClick={() => navigator.clipboard.writeText(script.content)}
              >
                <Copy className="h-3 w-3" /> Copy
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="gap-1 text-xs"
                onClick={() => onRegenerate({ assetKind: 'scripts', assetId: script.id })}
                disabled={isPending}
              >
                <RefreshCw className="h-3 w-3" /> Regenerate
              </Button>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

function ImagesTab({
  assets,
  onApprove,
  onRegenerate,
  isPending,
}: {
  assets: ImageAsset[]
  onApprove: (p: ApproveAssetPayload) => void
  onRegenerate: (p: RegeneratePayload) => void
  isPending?: boolean
}) {
  return (
    <div className="grid grid-cols-3 gap-4">
      {assets.map((img) => (
        <Card key={img.id}>
          <CardContent className="pt-4 space-y-2">
            <img
              src={img.url}
              alt={img.format}
              className="w-full rounded object-cover"
              style={{
                aspectRatio:
                  img.format === 'portrait' ? '3/4' : img.format === 'landscape' ? '16/9' : '1/1',
              }}
            />
            <div className="flex items-center justify-between">
              <Badge variant="outline" className="text-xs">
                {IMAGE_FORMAT_LABELS[img.format] ?? img.format}
              </Badge>
              {img.approved === true && (
                <Badge className="bg-green-600 text-white text-xs">Approved</Badge>
              )}
              {img.approved === false && (
                <Badge variant="destructive" className="text-xs">Rejected</Badge>
              )}
            </div>
            <div className="flex items-center gap-1 flex-wrap">
              <ApproveButtons
                approved={img.approved}
                onApprove={() =>
                  onApprove({ assetKind: 'images', assetId: img.id, approved: true })
                }
                onReject={() =>
                  onApprove({ assetKind: 'images', assetId: img.id, approved: false })
                }
                disabled={isPending}
              />
              <Button asChild variant="ghost" size="sm" className="gap-1 text-xs px-2">
                <a href={img.url} download>
                  <Download className="h-3 w-3" /> Download
                </a>
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="gap-1 text-xs"
                onClick={() => onRegenerate({ assetKind: 'images', assetId: img.id })}
                disabled={isPending}
              >
                <RefreshCw className="h-3 w-3" /> Regenerate
              </Button>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

function AudioTab({
  assets,
  onApprove,
  onRegenerate,
  isPending,
}: {
  assets: AudioAsset[]
  onApprove: (p: ApproveAssetPayload) => void
  onRegenerate: (p: RegeneratePayload) => void
  isPending?: boolean
}) {
  return (
    <div className="space-y-4">
      {assets.map((audio) => (
        <Card key={audio.id}>
          <CardContent className="pt-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex gap-2">
                <Badge variant="outline">
                  {MEDIA_FORMAT_LABELS[audio.format] ?? audio.format}
                </Badge>
                <Badge variant="secondary" className="text-xs">
                  {VOICE_LABELS[audio.voice_style] ?? audio.voice_style} voice
                </Badge>
                <Badge variant="secondary" className="text-xs">
                  {formatDuration(audio.duration_seconds)}
                </Badge>
              </div>
              {audio.approved === true && (
                <Badge className="bg-green-600 text-white text-xs">Approved</Badge>
              )}
              {audio.approved === false && (
                <Badge variant="destructive" className="text-xs">Rejected</Badge>
              )}
            </div>
            {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
            <audio controls src={audio.url} className="w-full" />
            <div className="flex items-center gap-2">
              <ApproveButtons
                approved={audio.approved}
                onApprove={() =>
                  onApprove({ assetKind: 'audio', assetId: audio.id, approved: true })
                }
                onReject={() =>
                  onApprove({ assetKind: 'audio', assetId: audio.id, approved: false })
                }
                disabled={isPending}
              />
              <Button asChild variant="ghost" size="sm" className="gap-1 text-xs px-2">
                <a href={audio.url} download>
                  <Download className="h-3 w-3" /> Download
                </a>
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="gap-1 text-xs"
                onClick={() => onRegenerate({ assetKind: 'audio', assetId: audio.id })}
                disabled={isPending}
              >
                <RefreshCw className="h-3 w-3" /> Regenerate
              </Button>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

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
            Generate copy, scripts, images, and audio assets for this campaign.
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
    return <p className="text-muted-foreground text-sm">Generating creatives… this may take a minute.</p>
  }

  if (status !== 'creative_ready' || !creative_assets) {
    return <p className="text-muted-foreground text-sm">No assets available.</p>
  }

  return (
    <div>
      <h2 className="text-lg font-semibold mb-4">Creative Assets</h2>
      <Tabs defaultValue="copy">
        <TabsList>
          <TabsTrigger value="copy">Copy</TabsTrigger>
          <TabsTrigger value="scripts">Scripts</TabsTrigger>
          <TabsTrigger value="images">Images</TabsTrigger>
          <TabsTrigger value="audio">Audio</TabsTrigger>
        </TabsList>
        <TabsContent value="copy" className="mt-4">
          <CopyTab
            assets={creative_assets.copy}
            onApprove={approveAsset.mutate}
            onRegenerate={regenerateAsset.mutate}
            isPending={approveAsset.isPending || regenerateAsset.isPending}
          />
        </TabsContent>
        <TabsContent value="scripts" className="mt-4">
          <ScriptsTab
            assets={creative_assets.scripts}
            onApprove={approveAsset.mutate}
            onRegenerate={regenerateAsset.mutate}
            isPending={approveAsset.isPending || regenerateAsset.isPending}
          />
        </TabsContent>
        <TabsContent value="images" className="mt-4">
          <ImagesTab
            assets={creative_assets.images}
            onApprove={approveAsset.mutate}
            onRegenerate={regenerateAsset.mutate}
            isPending={approveAsset.isPending || regenerateAsset.isPending}
          />
        </TabsContent>
        <TabsContent value="audio" className="mt-4">
          <AudioTab
            assets={creative_assets.audio}
            onApprove={approveAsset.mutate}
            onRegenerate={regenerateAsset.mutate}
            isPending={approveAsset.isPending || regenerateAsset.isPending}
          />
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
