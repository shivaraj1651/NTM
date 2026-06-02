# fe-creative — Design Spec

**Date:** 2026-05-16
**Session:** fe-creative
**Scope:** Extend the Campaign module with a Creatives stage — trigger generation, view, approve/reject, download, and re-generate copy, script, image, and audio assets.

---

## 1. Status Flow & Routing

### New campaign statuses

| Status | Meaning |
|---|---|
| `creative_generating` | Generation triggered, in-flight |
| `creative_ready` | All assets available |

**Full lifecycle:**
`pending → concepts_ready → confirmed → planned → budget_proposed → approved → creative_generating → creative_ready`

### Route

`/admin/campaigns/:id/creatives` — nested child of `CampaignDetailPage`, alongside `concepts`, `plan`, `budget`.

### Redirect logic (CampaignDetailPage)

| Status | Redirects to |
|---|---|
| `concepts_ready` | `/concepts` |
| `confirmed` \| `planned` | `/plan` |
| `budget_proposed` | `/budget` |
| `approved` \| `creative_generating` \| `creative_ready` | `/creatives` |

### Stepper

Adds one step at index 6: **Creatives**.

Updated arrays:
```typescript
const STEPS = ['Create', 'Concepts', 'Confirmed', 'Plan', 'Budget', 'Approved', 'Creatives']

const STATUS_TO_STEP: Record<CampaignStatus, number> = {
  pending: 0,
  concepts_ready: 1,
  confirmed: 2,
  planned: 3,
  budget_proposed: 4,
  approved: 5,
  creative_generating: 6,
  creative_ready: 6,
}

const STEP_PATHS = [null, 'concepts', 'plan', 'plan', 'budget', 'budget', 'creatives']
```

---

## 2. Data Model

### Types appended to `frontend/src/types/admin.ts`

```typescript
export type CopyAssetType =
  | 'social_caption' | 'headline' | 'body_copy'
  | 'print_ad' | 'email' | 'ooh_billboard' | 'influencer_brief'

export interface CopyVariant {
  variant: 'A' | 'B'
  content: string
  word_count: number
}

export interface CopyAsset {
  asset_type: CopyAssetType
  variants: CopyVariant[]
  approved: boolean | null
}

export interface ScriptAsset {
  id: string
  format: 'tvc_vo' | 'radio' | 'social_video'
  content: string
  duration_estimate: string
  approved: boolean | null
}

export interface ImageAsset {
  id: string
  format: 'square' | 'landscape' | 'portrait'
  url: string
  approved: boolean | null
}

export interface AudioAsset {
  id: string
  format: 'radio' | 'tvc_vo' | 'social_video'
  voice_style: 'warm' | 'authoritative' | 'youthful'
  url: string
  duration_seconds: number
  approved: boolean | null
}

export interface CreativeAssets {
  campaign_id: string
  copy: CopyAsset[]
  scripts: ScriptAsset[]
  images: ImageAsset[]
  audio: AudioAsset[]
}
```

### Modifications to existing types

**`CampaignStatus`** — add two new members:
```typescript
export type CampaignStatus =
  | 'pending' | 'concepts_ready' | 'confirmed'
  | 'planned' | 'budget_proposed' | 'approved'
  | 'creative_generating' | 'creative_ready'
```

**`Campaign`** — add one new field:
```typescript
creative_assets: CreativeAssets | null
```

---

## 3. MSW — Seed Data & Handlers

### Seed data (`frontend/src/mocks/db/campaigns.ts`)

- `c-003` (currently `approved`) updated to `creative_ready` with pre-populated `creative_assets`.
- New helper `generateCreativeAssets(campaignId: string): CreativeAssets` produces:
  - 7 `CopyAsset` entries, each with variant A + B (realistic placeholder copy)
  - 3 `ScriptAsset` entries (formats: `tvc_vo`, `radio`, `social_video`)
  - 3 `ImageAsset` entries (one per format, URLs: `https://placehold.co/1024x1024`, `https://placehold.co/1344x768`, `https://placehold.co/768x1344`)
  - 3 `AudioAsset` entries (one per voice style, URL: a public sample MP3)

### New handlers (`frontend/src/mocks/handlers/campaigns.ts`)

```
POST /api/v1/campaigns/:id/generate-creatives
  Sets status → 'creative_ready', attaches generateCreativeAssets(id)
  Returns updated campaign

PATCH /api/v1/campaigns/:id/creatives/copy/:asset_type
  Body: { approved: boolean }
  Updates CopyAsset.approved in campaignStore

PATCH /api/v1/campaigns/:id/creatives/scripts/:script_id
  Body: { approved: boolean }
  Updates ScriptAsset.approved

PATCH /api/v1/campaigns/:id/creatives/images/:image_id
  Body: { approved: boolean }
  Updates ImageAsset.approved

PATCH /api/v1/campaigns/:id/creatives/audio/:audio_id
  Body: { approved: boolean }
  Updates AudioAsset.approved

POST /api/v1/campaigns/:id/creatives/copy/:asset_type/regenerate
  Replaces the matching CopyAsset with freshly generated variants

POST /api/v1/campaigns/:id/creatives/scripts/:script_id/regenerate
  Replaces the matching ScriptAsset with new content

POST /api/v1/campaigns/:id/creatives/images/:image_id/regenerate
  Replaces the matching ImageAsset with a new url (cache-busted placehold.co)

POST /api/v1/campaigns/:id/creatives/audio/:audio_id/regenerate
  Replaces the matching AudioAsset
```

---

## 4. React Query Hooks (`frontend/src/hooks/useCampaigns.ts`)

Three new hooks appended:

```typescript
useGenerateCreatives(campaignId: string)
  // useMutation — POST generate-creatives
  // onSuccess: invalidate ['campaign', campaignId]

useApproveCreativeAsset(campaignId: string)
  // useMutation<void, unknown, ApproveAssetPayload>
  // ApproveAssetPayload: { assetKind, assetId, approved }
  // Routes to the correct PATCH endpoint based on assetKind
  // onSuccess: invalidate ['campaign', campaignId]

useRegenerateAsset(campaignId: string)
  // useMutation<void, unknown, RegeneratePayload>
  // RegeneratePayload: { assetKind, assetId }
  // Routes to the correct POST regenerate endpoint
  // onSuccess: invalidate ['campaign', campaignId]
```

---

## 5. CreativesPage (`frontend/src/pages/Admin/Campaigns/CreativesPage.tsx`)

### Pre-generation state (status `approved`)

- Heading "Creative Assets" + brief description
- "Generate Creatives" button
- While mutation `isPending`: button replaced by spinner + "Generating assets…" text

### Post-generation state (status `creative_ready`)

Four tabs rendered via shadcn `<Tabs>`: **Copy | Scripts | Images | Audio**

#### Copy tab

Accordion (shadcn `<Accordion>`), one `AccordionItem` per asset type (7 total). Label = humanised asset type name.

Expanded content: two side-by-side cards (Variant A, Variant B). Each card:
- Scrollable text content
- Word count `<Badge>`
- Approve ✓ / Reject ✗ toggle buttons (green/red when active, `outline` variant otherwise)
- Copy-to-clipboard `<Button variant="ghost" size="sm">`
- Regenerate `<Button variant="ghost" size="sm">` (re-generates both variants for this asset type)

#### Scripts tab

Vertical list of cards. Each card:
- Format badge + duration estimate
- Pre-formatted scrollable script text (`<pre>` or `whitespace-pre-wrap`)
- Approve/Reject toggle, copy-to-clipboard, Regenerate

#### Images tab

3-column CSS grid. Each cell:
- `<img>` with `object-cover`, aspect ratio preserved by format
- Format label below
- Approve/Reject toggle
- Download: `<a href={url} download>` button
- Regenerate button

#### Audio tab

Vertical list. Each row:
- Voice style + format badges
- HTML5 `<audio controls src={url} />` player
- Duration (formatted as `mm:ss`)
- Approve/Reject toggle
- Download anchor, Regenerate button

---

## 6. Modified Files

| File | Change |
|---|---|
| `frontend/src/types/admin.ts` | Add new types + extend `CampaignStatus` + `Campaign.creative_assets` |
| `frontend/src/mocks/db/campaigns.ts` | Add `generateCreativeAssets`, update `c-003`, add `creative_generating/ready` to type |
| `frontend/src/mocks/handlers/campaigns.ts` | Add 8 new handlers |
| `frontend/src/hooks/useCampaigns.ts` | Add 3 new hooks |
| `frontend/src/pages/Admin/Campaigns/CampaignDetailPage.tsx` | Update stepper arrays + redirect useEffect |
| `frontend/src/pages/Admin/Campaigns/CreativesPage.tsx` | New file |
| `frontend/src/App.tsx` | Add `creatives` child route |

**BudgetPage.tsx — no changes needed.** The `approved` redirect is now handled by `CampaignDetailPage`, and the approved banner remains accessible via the completed step link in the stepper.
