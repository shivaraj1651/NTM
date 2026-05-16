# fe-creative Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the Campaign module with a Creatives stage — trigger generation, then view, approve/reject, download, and re-generate copy, script, image, and audio assets on a tabbed page.

**Architecture:** Two new `CampaignStatus` values (`creative_generating`, `creative_ready`). `CampaignDetailPage` stepper gains a 7th step. A new `CreativesPage` renders a "Generate" button (pre-generation) or 4 shadcn `<Tabs>` (post-generation). All data via MSW — `POST /generate-creatives` immediately returns `creative_ready` with assets; approve/reject and regenerate via PATCH and POST endpoints.

**Tech Stack:** React 18, TypeScript, Vite, shadcn/ui (Accordion + Tabs — not yet installed), TanStack Query v5, MSW v2, react-router-dom v7, lucide-react.

---

## File Map

| File | Action |
|---|---|
| `frontend/src/types/admin.ts` | Append 6 new interfaces + extend `CampaignStatus` + add `creative_assets` to `Campaign` |
| `frontend/src/mocks/db/campaigns.ts` | Add `generateCreativeAssets`, update c-003 to `creative_ready`, add `creative_assets: null` to c-001/c-002 and new-campaign factory |
| `frontend/src/mocks/handlers/campaigns.ts` | Add 3 new handlers (generate, approve, regenerate), patch new-campaign factory |
| `frontend/src/api/admin.ts` | Append 3 API client functions |
| `frontend/src/hooks/useCampaigns.ts` | Append 2 payload types + 3 hooks |
| `frontend/src/pages/Admin/Campaigns/CampaignDetailPage.tsx` | Update `STEPS`, `STATUS_TO_STEP`, `STEP_PATHS`, and redirect `useEffect` |
| `frontend/src/pages/Admin/Campaigns/CreativesPage.tsx` | New file — full component |
| `frontend/src/App.tsx` | Add `creatives` child route |

---

### Task 1: Campaign Types

**Files:**
- Modify: `frontend/src/types/admin.ts`

- [ ] **Step 1: Extend `CampaignStatus`**

In `frontend/src/types/admin.ts`, replace:

```typescript
export type CampaignStatus =
  | 'pending'
  | 'concepts_ready'
  | 'confirmed'
  | 'planned'
  | 'budget_proposed'
  | 'approved'
```

with:

```typescript
export type CampaignStatus =
  | 'pending'
  | 'concepts_ready'
  | 'confirmed'
  | 'planned'
  | 'budget_proposed'
  | 'approved'
  | 'creative_generating'
  | 'creative_ready'
```

- [ ] **Step 2: Add `creative_assets` to `Campaign`**

In `frontend/src/types/admin.ts`, replace:

```typescript
export interface Campaign {
  id: string
  mandate_id: string
  tenant_id: string
  status: CampaignStatus
  concepts: CampaignConcept[]
  selected_concept_id: string | null
  activation_plan: Activation[]
  budget_proposal: BudgetProposal | null
  created_at: string
  updated_at: string
}
```

with:

```typescript
export interface Campaign {
  id: string
  mandate_id: string
  tenant_id: string
  status: CampaignStatus
  concepts: CampaignConcept[]
  selected_concept_id: string | null
  activation_plan: Activation[]
  budget_proposal: BudgetProposal | null
  creative_assets: CreativeAssets | null
  created_at: string
  updated_at: string
}
```

- [ ] **Step 3: Append creative asset types**

Append at the very end of `frontend/src/types/admin.ts`:

```typescript
export type CopyAssetType =
  | 'social_caption'
  | 'headline'
  | 'body_copy'
  | 'print_ad'
  | 'email'
  | 'ooh_billboard'
  | 'influencer_brief'

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

- [ ] **Step 4: Type-check**

```
cd frontend && npx tsc --noEmit
```

Expected: errors about missing `creative_assets` in seed data — that's fine, fixed in Task 2.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/admin.ts
git commit -m "[TASK-020] feat: add creative asset types and extend CampaignStatus"
```

---

### Task 2: MSW Seed Data

**Files:**
- Modify: `frontend/src/mocks/db/campaigns.ts`

- [ ] **Step 1: Update the import line**

Replace the first line of `frontend/src/mocks/db/campaigns.ts`:

```typescript
import type { Campaign, Mandate, CampaignConcept, Activation, BudgetProposal } from '@/types/admin'
```

with:

```typescript
import type {
  Campaign,
  Mandate,
  CampaignConcept,
  Activation,
  BudgetProposal,
  CreativeAssets,
  CopyAsset,
  ScriptAsset,
  ImageAsset,
  AudioAsset,
} from '@/types/admin'
```

- [ ] **Step 2: Add `generateCreativeAssets` helper**

Append the following function at the end of `frontend/src/mocks/db/campaigns.ts` (after `generateBudgetProposal`):

```typescript
export function generateCreativeAssets(campaignId: string): CreativeAssets {
  const copy: CopyAsset[] = [
    {
      asset_type: 'social_caption',
      variants: [
        { variant: 'A', content: 'Ready to transform your business? Our solutions help you scale faster than ever. #Innovation #Growth', word_count: 17 },
        { variant: 'B', content: 'Join 500+ companies already growing with us. Start your journey today. #BusinessGrowth', word_count: 14 },
      ],
      approved: null,
    },
    {
      asset_type: 'headline',
      variants: [
        { variant: 'A', content: 'Scale Smarter. Grow Faster. Win Bigger.', word_count: 6 },
        { variant: 'B', content: 'The Future of Business Starts Here.', word_count: 7 },
      ],
      approved: null,
    },
    {
      asset_type: 'body_copy',
      variants: [
        { variant: 'A', content: 'In today\'s competitive landscape, every decision counts. Our platform gives you the insights, tools, and support to outpace the competition. From real-time analytics to automated workflows, we\'ve built everything you need to grow with confidence.', word_count: 42 },
        { variant: 'B', content: 'What separates thriving businesses from struggling ones? Better data, faster decisions, and the right partner. That\'s what we deliver — proven results for companies like yours, backed by 10 years of expertise.', word_count: 35 },
      ],
      approved: null,
    },
    {
      asset_type: 'print_ad',
      variants: [
        { variant: 'A', content: 'HEADLINE: Your Growth, Amplified.\nBODY: We turn strategy into results. 500+ clients. 3× average ROI. Trusted by leaders in 40 countries.\nCTA: Get Started Today', word_count: 27 },
        { variant: 'B', content: 'HEADLINE: Don\'t Just Compete. Dominate.\nBODY: Market leaders choose us for precision targeting, unmatched reach, and measurable impact.\nCTA: See How We Do It', word_count: 24 },
      ],
      approved: null,
    },
    {
      asset_type: 'email',
      variants: [
        { variant: 'A', content: 'Subject: You\'re leaving money on the table\n\nHi [First Name],\n\nMost businesses only capture 30% of their growth potential. The other 70%? It\'s sitting in untapped channels and missed opportunities.\n\nWe fix that. Book a free 30-minute strategy session.\n\n[Book My Session]', word_count: 50 },
        { variant: 'B', content: 'Subject: Quick question about your Q3 targets\n\nHi [First Name],\n\nAre you on track to hit your Q3 goals? Our team has helped 200+ businesses close their growth gap — often within 60 days.\n\nNo obligation. Just clarity.\n\n[Schedule a Call]', word_count: 46 },
      ],
      approved: null,
    },
    {
      asset_type: 'ooh_billboard',
      variants: [
        { variant: 'A', content: 'GROW BOLD.\n[Logo] — example.com', word_count: 4 },
        { variant: 'B', content: 'RESULTS YOU CAN SEE.\n[Logo] — example.com', word_count: 5 },
      ],
      approved: null,
    },
    {
      asset_type: 'influencer_brief',
      variants: [
        { variant: 'A', content: 'CAMPAIGN BRIEF — Influencer Partnership\n\nObjective: Drive awareness among 25–40 professionals.\nKey Message: Our platform makes growing your business effortless.\nTone: Authentic, conversational — not salesy.\nMandatories: Mention the free trial. Tag @Brand. Use #GrowBold.\nDeliverables: 1× feed post + 3× Stories with link sticker.', word_count: 56 },
        { variant: 'B', content: 'INFLUENCER GUIDE — Brand Collaboration\n\nWhat we want: Show your real workflow using our tools.\nDon\'t: Read from a script or make it feel like an ad.\nDo: Be genuine. Share a specific win.\nMust-haves: Disclose partnership, tag @Brand, include swipe-up link.\nFormat: 60–90 second Reel or TikTok preferred.', word_count: 55 },
      ],
      approved: null,
    },
  ]

  const scripts: ScriptAsset[] = [
    {
      id: `${campaignId}-scr-1`,
      format: 'tvc_vo',
      content: '[OPEN ON: Busy city office, professionals at work]\n\nVO: Every day, thousands of decisions shape your business future.\n\n[CUT TO: Dashboard with rising metrics]\n\nVO: What if you had the clarity to make every one count?\n\n[CUT TO: Satisfied team celebrating]\n\nVO: [Brand]. Decisions made smarter.\n\n[SUPER: example.com]',
      duration_estimate: '30s',
      approved: null,
    },
    {
      id: `${campaignId}-scr-2`,
      format: 'radio',
      content: 'SFX: Upbeat music, fades under VO\n\nVO: Struggling to hit your growth targets? You\'re not alone — but you don\'t have to stay stuck. [Brand] helps businesses like yours unlock real, measurable growth. More leads. Better conversions. Higher ROI.\n\nVisit example.com and start your free trial. [Brand] — Grow Bolder.\n\nSFX: Music up and out',
      duration_estimate: '30s',
      approved: null,
    },
    {
      id: `${campaignId}-scr-3`,
      format: 'social_video',
      content: '[0:00–0:03] HOOK: Text overlay — "Still doing this manually?"\n[0:03–0:10] Pain point: spreadsheets, manual tracking\n[0:10–0:20] Product reveal: dashboard auto-updating in real time\n[0:20–0:25] Social proof: "Trusted by 500+ teams"\n[0:25–0:30] CTA: "Try free — link in bio"\n\nCaption: Work smarter, not harder. #ProductivityHack #GrowthMindset',
      duration_estimate: '30s',
      approved: null,
    },
  ]

  const images: ImageAsset[] = [
    { id: `${campaignId}-img-1`, format: 'square',    url: 'https://placehold.co/1024x1024/1a1a2e/ffffff?text=Square+Ad',    approved: null },
    { id: `${campaignId}-img-2`, format: 'landscape', url: 'https://placehold.co/1344x768/16213e/ffffff?text=Landscape+Ad', approved: null },
    { id: `${campaignId}-img-3`, format: 'portrait',  url: 'https://placehold.co/768x1344/0f3460/ffffff?text=Portrait+Ad',  approved: null },
  ]

  const audio: AudioAsset[] = [
    { id: `${campaignId}-aud-1`, format: 'radio',        voice_style: 'warm',          url: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3', duration_seconds: 30, approved: null },
    { id: `${campaignId}-aud-2`, format: 'tvc_vo',       voice_style: 'authoritative', url: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3', duration_seconds: 30, approved: null },
    { id: `${campaignId}-aud-3`, format: 'social_video', voice_style: 'youthful',      url: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3', duration_seconds: 30, approved: null },
  ]

  return { campaign_id: campaignId, copy, scripts, images, audio }
}
```

- [ ] **Step 3: Add `creative_assets: null` to c-001 and c-002**

In `frontend/src/mocks/db/campaigns.ts`, find c-001's definition and add `creative_assets: null` after `budget_proposal: null`:

```typescript
  'c-001': {
    id: 'c-001',
    mandate_id: 'm-001',
    tenant_id: 't1',
    status: 'concepts_ready',
    concepts: baseConcepts,
    selected_concept_id: null,
    activation_plan: [],
    budget_proposal: null,
    creative_assets: null,
    created_at: '2026-05-10T09:00:00Z',
    updated_at: '2026-05-10T09:05:00Z',
  },
```

And c-002 (after `budget_proposal: null`):

```typescript
  'c-002': {
    id: 'c-002',
    mandate_id: 'm-001',
    tenant_id: 't1',
    status: 'planned',
    concepts: baseConcepts,
    selected_concept_id: 'con-001',
    activation_plan: baseActivations,
    budget_proposal: null,
    creative_assets: null,
    created_at: '2026-05-08T11:00:00Z',
    updated_at: '2026-05-08T14:30:00Z',
  },
```

- [ ] **Step 4: Update c-003 to `creative_ready` with assets**

Replace c-003 in `initialCampaigns`:

```typescript
  'c-003': {
    id: 'c-003',
    mandate_id: 'm-002',
    tenant_id: 't1',
    status: 'creative_ready',
    concepts: baseConcepts,
    selected_concept_id: 'con-002',
    activation_plan: baseActivations,
    budget_proposal: baseBudgetProposal,
    creative_assets: {
      campaign_id: 'c-003',
      copy: [],
      scripts: [],
      images: [],
      audio: [],
    },
    created_at: '2026-05-05T10:00:00Z',
    updated_at: '2026-05-12T16:00:00Z',
  },
```

Note: c-003's `creative_assets` is intentionally an empty shell here — the `generateCreativeAssets` call happens via the MSW handler when "Generate Creatives" is clicked. To show a pre-populated example, replace the empty arrays with `...generateCreativeAssets('c-003')` spread — but this requires `generateCreativeAssets` to be defined before `initialCampaigns`. Move the function definition above `initialCampaigns`, then use:

```typescript
  'c-003': {
    id: 'c-003',
    mandate_id: 'm-002',
    tenant_id: 't1',
    status: 'creative_ready',
    concepts: baseConcepts,
    selected_concept_id: 'con-002',
    activation_plan: baseActivations,
    budget_proposal: baseBudgetProposal,
    creative_assets: generateCreativeAssets('c-003'),
    created_at: '2026-05-05T10:00:00Z',
    updated_at: '2026-05-12T16:00:00Z',
  },
```

- [ ] **Step 5: Type-check**

```
cd frontend && npx tsc --noEmit
```

Expected: no errors (or only errors about handlers — fixed in Task 3).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/mocks/db/campaigns.ts
git commit -m "[TASK-020] feat: add creative asset seed data and generateCreativeAssets helper"
```

---

### Task 3: MSW Handlers

**Files:**
- Modify: `frontend/src/mocks/handlers/campaigns.ts`

- [ ] **Step 1: Patch the POST /campaigns factory to include `creative_assets: null`**

In `frontend/src/mocks/handlers/campaigns.ts`, in the `http.post('/api/v1/campaigns', ...)` handler, add `creative_assets: null` to `newCampaign`:

```typescript
    const newCampaign: Campaign = {
      id: newId,
      mandate_id,
      tenant_id: mandate.tenant_id,
      status: 'concepts_ready',
      concepts: db.generateConcepts(mandate_id),
      selected_concept_id: null,
      activation_plan: [],
      budget_proposal: null,
      creative_assets: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
```

- [ ] **Step 2: Append 3 new handlers before the closing `]`**

In `frontend/src/mocks/handlers/campaigns.ts`, replace the closing `]` with the following (insert before the closing bracket):

```typescript
  http.post('/api/v1/campaigns/:id/generate-creatives', ({ params }) => {
    const campaign = db.campaignStore[params.id as string]
    if (!campaign) return new HttpResponse(null, { status: 404 })
    db.campaignStore[campaign.id] = {
      ...campaign,
      status: 'creative_ready',
      creative_assets: db.generateCreativeAssets(campaign.id),
      updated_at: new Date().toISOString(),
    }
    return HttpResponse.json(db.campaignStore[campaign.id])
  }),

  http.patch('/api/v1/campaigns/:id/creatives/:assetKind/:assetId', async ({ params, request }) => {
    const campaign = db.campaignStore[params.id as string]
    if (!campaign?.creative_assets) return new HttpResponse(null, { status: 404 })
    const { approved } = (await request.json()) as { approved: boolean }
    const { assetKind, assetId } = params as { assetKind: string; assetId: string }
    let assets = campaign.creative_assets
    if (assetKind === 'copy') {
      assets = { ...assets, copy: assets.copy.map((a) => a.asset_type === assetId ? { ...a, approved } : a) }
    } else if (assetKind === 'scripts') {
      assets = { ...assets, scripts: assets.scripts.map((s) => s.id === assetId ? { ...s, approved } : s) }
    } else if (assetKind === 'images') {
      assets = { ...assets, images: assets.images.map((i) => i.id === assetId ? { ...i, approved } : i) }
    } else if (assetKind === 'audio') {
      assets = { ...assets, audio: assets.audio.map((a) => a.id === assetId ? { ...a, approved } : a) }
    }
    db.campaignStore[campaign.id] = { ...campaign, creative_assets: assets, updated_at: new Date().toISOString() }
    return HttpResponse.json(db.campaignStore[campaign.id])
  }),

  http.post('/api/v1/campaigns/:id/creatives/:assetKind/:assetId/regenerate', ({ params }) => {
    const campaign = db.campaignStore[params.id as string]
    if (!campaign?.creative_assets) return new HttpResponse(null, { status: 404 })
    const { assetKind, assetId } = params as { assetKind: string; assetId: string }
    const fresh = db.generateCreativeAssets(campaign.id)
    let assets = campaign.creative_assets

    if (assetKind === 'copy') {
      const freshAsset = fresh.copy.find((a) => a.asset_type === assetId)
      if (freshAsset) {
        assets = { ...assets, copy: assets.copy.map((a) => a.asset_type === assetId ? { ...freshAsset, approved: null } : a) }
      }
    } else if (assetKind === 'scripts') {
      const idx = assets.scripts.findIndex((s) => s.id === assetId)
      if (idx >= 0 && fresh.scripts[idx]) {
        const updated = [...assets.scripts]
        updated[idx] = { ...fresh.scripts[idx], id: assetId, approved: null }
        assets = { ...assets, scripts: updated }
      }
    } else if (assetKind === 'images') {
      const IMAGE_SIZES: Record<string, string> = {
        square: '1024x1024/1a1a2e/ffffff?text=Square+Ad',
        landscape: '1344x768/16213e/ffffff?text=Landscape+Ad',
        portrait: '768x1344/0f3460/ffffff?text=Portrait+Ad',
      }
      assets = {
        ...assets,
        images: assets.images.map((img) =>
          img.id === assetId
            ? { ...img, url: `https://placehold.co/${IMAGE_SIZES[img.format]}&t=${Date.now()}`, approved: null }
            : img
        ),
      }
    } else if (assetKind === 'audio') {
      const AUDIO_POOL = [
        'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3',
        'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3',
        'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3',
      ]
      const idx = assets.audio.findIndex((a) => a.id === assetId)
      if (idx >= 0) {
        const updated = [...assets.audio]
        updated[idx] = { ...updated[idx], url: AUDIO_POOL[(idx + 1) % AUDIO_POOL.length], approved: null }
        assets = { ...assets, audio: updated }
      }
    }

    db.campaignStore[campaign.id] = { ...campaign, creative_assets: assets, updated_at: new Date().toISOString() }
    return HttpResponse.json(db.campaignStore[campaign.id])
  }),
```

- [ ] **Step 3: Type-check**

```
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/mocks/handlers/campaigns.ts
git commit -m "[TASK-020] feat: add MSW handlers for generate-creatives, approve, and regenerate"
```

---

### Task 4: API Client + Hooks

**Files:**
- Modify: `frontend/src/api/admin.ts`
- Modify: `frontend/src/hooks/useCampaigns.ts`

- [ ] **Step 1: Append 3 API client functions to `frontend/src/api/admin.ts`**

```typescript
export const generateCreatives = (id: string) =>
  apiClient.post(`/campaigns/${id}/generate-creatives`).then((r) => r.data)

export const approveCreativeAsset = (
  id: string,
  assetKind: string,
  assetId: string,
  approved: boolean,
) =>
  apiClient
    .patch(`/campaigns/${id}/creatives/${assetKind}/${assetId}`, { approved })
    .then((r) => r.data)

export const regenerateAsset = (id: string, assetKind: string, assetId: string) =>
  apiClient
    .post(`/campaigns/${id}/creatives/${assetKind}/${assetId}/regenerate`)
    .then((r) => r.data)
```

- [ ] **Step 2: Append payload types + 3 hooks to `frontend/src/hooks/useCampaigns.ts`**

Add these imports at the top of `useCampaigns.ts` (the existing import from `@/api/admin` needs the 3 new functions):

Replace the existing import line:

```typescript
import {
  getCampaigns,
  getCampaign,
  createCampaign,
  confirmConcept,
  getActivationPlan,
  approveBudget,
  confirmBudget,
  getMandates,
} from '@/api/admin'
```

with:

```typescript
import {
  getCampaigns,
  getCampaign,
  createCampaign,
  confirmConcept,
  getActivationPlan,
  approveBudget,
  confirmBudget,
  getMandates,
  generateCreatives,
  approveCreativeAsset,
  regenerateAsset,
} from '@/api/admin'
```

Then append at the end of `useCampaigns.ts`:

```typescript
type AssetKind = 'copy' | 'scripts' | 'images' | 'audio'

export interface ApproveAssetPayload {
  assetKind: AssetKind
  assetId: string
  approved: boolean
}

export interface RegeneratePayload {
  assetKind: AssetKind
  assetId: string
}

export function useGenerateCreatives(campaignId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => generateCreatives(campaignId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['campaign', campaignId] }),
  })
}

export function useApproveCreativeAsset(campaignId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ assetKind, assetId, approved }: ApproveAssetPayload) =>
      approveCreativeAsset(campaignId, assetKind, assetId, approved),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['campaign', campaignId] }),
  })
}

export function useRegenerateAsset(campaignId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ assetKind, assetId }: RegeneratePayload) =>
      regenerateAsset(campaignId, assetKind, assetId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['campaign', campaignId] }),
  })
}
```

- [ ] **Step 3: Type-check**

```
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/admin.ts frontend/src/hooks/useCampaigns.ts
git commit -m "[TASK-020] feat: add creative asset API client functions and React Query hooks"
```

---

### Task 5: CampaignDetailPage — Stepper + Redirect

**Files:**
- Modify: `frontend/src/pages/Admin/Campaigns/CampaignDetailPage.tsx`

- [ ] **Step 1: Update `STEPS`, `STATUS_TO_STEP`, and `STEP_PATHS`**

Replace:

```typescript
const STEPS = ['Create', 'Concepts', 'Confirmed', 'Plan', 'Budget', 'Approved']

const STATUS_TO_STEP: Record<CampaignStatus, number> = {
  pending: 0,
  concepts_ready: 1,
  confirmed: 2,
  planned: 3,
  budget_proposed: 4,
  approved: 5,
}

const STEP_PATHS = [null, 'concepts', 'plan', 'plan', 'budget', 'budget']
```

with:

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

- [ ] **Step 2: Update the redirect `useEffect`**

Replace:

```typescript
  useEffect(() => {
    if (!campaign) return
    const base = `/admin/campaigns/${id}`
    if (location.pathname !== base && location.pathname !== `${base}/`) return
    const { status } = campaign
    if (status === 'concepts_ready') navigate(`${base}/concepts`, { replace: true })
    else if (status === 'confirmed' || status === 'planned') navigate(`${base}/plan`, { replace: true })
    else if (status === 'budget_proposed' || status === 'approved') navigate(`${base}/budget`, { replace: true })
  }, [campaign, id, navigate, location.pathname])
```

with:

```typescript
  useEffect(() => {
    if (!campaign) return
    const base = `/admin/campaigns/${id}`
    if (location.pathname !== base && location.pathname !== `${base}/`) return
    const { status } = campaign
    if (status === 'concepts_ready') navigate(`${base}/concepts`, { replace: true })
    else if (status === 'confirmed' || status === 'planned') navigate(`${base}/plan`, { replace: true })
    else if (status === 'budget_proposed') navigate(`${base}/budget`, { replace: true })
    else if (
      status === 'approved' ||
      status === 'creative_generating' ||
      status === 'creative_ready'
    ) navigate(`${base}/creatives`, { replace: true })
  }, [campaign, id, navigate, location.pathname])
```

- [ ] **Step 3: Type-check**

```
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Admin/Campaigns/CampaignDetailPage.tsx
git commit -m "[TASK-020] feat: extend CampaignDetailPage stepper with Creatives step"
```

---

### Task 6: Install shadcn Components + CreativesPage

**Files:**
- Create: `frontend/src/pages/Admin/Campaigns/CreativesPage.tsx`

- [ ] **Step 1: Install Accordion and Tabs shadcn components**

```
cd frontend && npx shadcn@latest add accordion tabs
```

Expected: creates `frontend/src/components/ui/accordion.tsx` and `frontend/src/components/ui/tabs.tsx`.

- [ ] **Step 2: Create `CreativesPage.tsx`**

Create `frontend/src/pages/Admin/Campaigns/CreativesPage.tsx` with the following content:

```typescript
import { useParams } from 'react-router-dom'
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
}: {
  approved: boolean | null
  onApprove: () => void
  onReject: () => void
}) {
  return (
    <div className="flex gap-1">
      <Button
        variant={approved === true ? 'default' : 'outline'}
        size="sm"
        className={approved === true ? 'bg-green-600 hover:bg-green-700 text-white' : ''}
        onClick={onApprove}
      >
        <Check className="h-3 w-3" />
      </Button>
      <Button
        variant={approved === false ? 'default' : 'outline'}
        size="sm"
        className={approved === false ? 'bg-red-600 hover:bg-red-700 text-white' : ''}
        onClick={onReject}
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
}: {
  assets: CopyAsset[]
  onApprove: (p: ApproveAssetPayload) => void
  onRegenerate: (p: RegeneratePayload) => void
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
                />
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1 text-xs"
                  onClick={() => onRegenerate({ assetKind: 'copy', assetId: asset.asset_type })}
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
}: {
  assets: ScriptAsset[]
  onApprove: (p: ApproveAssetPayload) => void
  onRegenerate: (p: RegeneratePayload) => void
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
}: {
  assets: ImageAsset[]
  onApprove: (p: ApproveAssetPayload) => void
  onRegenerate: (p: RegeneratePayload) => void
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
              />
              <a href={img.url} download>
                <Button variant="ghost" size="sm" className="gap-1 text-xs px-2">
                  <Download className="h-3 w-3" /> Download
                </Button>
              </a>
              <Button
                variant="outline"
                size="sm"
                className="gap-1 text-xs"
                onClick={() => onRegenerate({ assetKind: 'images', assetId: img.id })}
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
}: {
  assets: AudioAsset[]
  onApprove: (p: ApproveAssetPayload) => void
  onRegenerate: (p: RegeneratePayload) => void
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
                  {VOICE_LABELS[audio.voice_style]} voice
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
              />
              <a href={audio.url} download>
                <Button variant="ghost" size="sm" className="gap-1 text-xs px-2">
                  <Download className="h-3 w-3" /> Download
                </Button>
              </a>
              <Button
                variant="outline"
                size="sm"
                className="gap-1 text-xs"
                onClick={() => onRegenerate({ assetKind: 'audio', assetId: audio.id })}
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
  const { data: campaign } = useCampaign(id!)
  const generateCreatives = useGenerateCreatives(id!)
  const approveAsset = useApproveCreativeAsset(id!)
  const regenerateAsset = useRegenerateAsset(id!)

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

  if (!creative_assets) {
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
          />
        </TabsContent>
        <TabsContent value="scripts" className="mt-4">
          <ScriptsTab
            assets={creative_assets.scripts}
            onApprove={approveAsset.mutate}
            onRegenerate={regenerateAsset.mutate}
          />
        </TabsContent>
        <TabsContent value="images" className="mt-4">
          <ImagesTab
            assets={creative_assets.images}
            onApprove={approveAsset.mutate}
            onRegenerate={regenerateAsset.mutate}
          />
        </TabsContent>
        <TabsContent value="audio" className="mt-4">
          <AudioTab
            assets={creative_assets.audio}
            onApprove={approveAsset.mutate}
            onRegenerate={regenerateAsset.mutate}
          />
        </TabsContent>
      </Tabs>
    </div>
  )
}
```

- [ ] **Step 3: Type-check**

```
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Admin/Campaigns/CreativesPage.tsx frontend/src/components/ui/accordion.tsx frontend/src/components/ui/tabs.tsx
git commit -m "[TASK-020] feat: add CreativesPage with tabbed copy, scripts, images, and audio panels"
```

---

### Task 7: Routing + Build Verify

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Add `CreativesPage` import and route to `App.tsx`**

Add import after the `BudgetPage` import line:

```typescript
import { CreativesPage } from '@/pages/Admin/Campaigns/CreativesPage'
```

Inside the `campaigns/:id` children array, add after the `budget` route:

```typescript
{ path: 'creatives', element: <CreativesPage /> },
```

The full `campaigns/:id` children block should now read:

```typescript
{
  path: 'campaigns/:id',
  element: <CampaignDetailPage />,
  children: [
    { path: 'concepts', element: <ConceptsPage /> },
    { path: 'plan', element: <PlanPage /> },
    { path: 'budget', element: <BudgetPage /> },
    { path: 'creatives', element: <CreativesPage /> },
  ],
},
```

- [ ] **Step 2: Type-check**

```
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Build**

```
cd frontend && npm run build
```

Expected: `✓ built in Xs` with no TypeScript errors. The chunk-size warning is fine.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "[TASK-020] feat: add creatives route and complete Campaign module"
```
