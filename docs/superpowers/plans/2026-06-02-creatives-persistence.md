# Creatives Persistence — Creative Studio Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix Creative Studio so generated creatives persist across page refresh and re-login by making `creativesStore` the single source of truth for all creative data.

**Architecture:** Three MSW mock files are patched. `flattenCreativeAssets()` converts the nested `CreativeAssets` shape to flat `Creative[]` objects keyed by id in `creativesStore` (localStorage-backed Proxy). The `/creatives` handlers read/write the store. The `generate-creatives` campaign handler populates the store on generation. Seed campaigns `c-003`/`c-004` pre-populate the store at module load.

**Tech Stack:** MSW v2, Vitest, React 18, TypeScript, localStorage

---

## File Map

| File | Change |
|------|--------|
| `frontend/src/mocks/db/campaigns.ts` | Add `flattenCreativeAssets()` export; call `_seedCreativesFromInitial()` after `campaignStore` |
| `frontend/src/mocks/handlers/creatives.ts` | Replace static `MOCK_CREATIVES` with `creativesStore` reads/writes |
| `frontend/src/mocks/handlers/campaigns.ts` | After `generate-creatives`, call `flattenCreativeAssets` and write to `creativesStore` |
| `frontend/src/test/creatives-persist.test.ts` | Unit tests for `flattenCreativeAssets` + mock handler behaviour |

---

## Task 1: Add `flattenCreativeAssets` + startup seeding to `db/campaigns.ts`

**Files:**
- Modify: `frontend/src/mocks/db/campaigns.ts`

**Context:** `creativesStore` is defined at line 53 as `createPersistedStore<any>('ntm:creatives', {})` but is always empty. `initialCampaigns` is defined at line 257; `campaignStore` at line 325. We must add `flattenCreativeAssets` after `generateCreativeAssets` and seed `creativesStore` after `campaignStore` (bottom of file) so all symbols are available.

The `CreativeStudioPage` reads these `content` fields per type:
- **image**: `content?.['url']` (for `<img src>`), `content?.['label']` (badge), `content?.['tagline']`, `content?.['campaign_theme']`
- **copy**: `content?.['asset_type']`, `content?.['label']`, `content?.['preview']`
- **script**: `content?.['format']`, `content?.['label']`, `content?.['duration_estimate']`, `content?.['content_preview']`
- **audio/other**: `content?.['label']`

- [ ] **Step 1: Add `flattenCreativeAssets` function**

Open `frontend/src/mocks/db/campaigns.ts`. Add this function immediately **after** the closing brace of `generateCreativeAssets` (after line ~254, before `const initialCampaigns`):

```typescript
export function flattenCreativeAssets(
  campaignId: string,
  assets: CreativeAssets,
): Record<string, unknown>[] {
  const now = new Date().toISOString()
  const flat: Record<string, unknown>[] = []

  assets.images.forEach((img, i) => {
    flat.push({
      id: (img as any).id ?? `${campaignId}-img-${i}`,
      campaign_id: campaignId,
      creative_type: 'image',
      platform: img.format,
      content: {
        url: img.url,
        label: img.format.replace(/_/g, ' '),
        tagline: null,
        campaign_theme: null,
      },
      validation_status: 'ai_draft',
      created_at: now,
      updated_at: null,
    })
  })

  assets.copy.forEach((copy, i) => {
    flat.push({
      id: `${campaignId}-copy-${i}`,
      campaign_id: campaignId,
      creative_type: 'copy',
      platform: copy.asset_type,
      content: {
        asset_type: copy.asset_type,
        label: copy.asset_type.replace(/_/g, ' '),
        preview: copy.variants[0]?.content?.slice(0, 120) ?? '',
      },
      validation_status: 'ai_draft',
      created_at: now,
      updated_at: null,
    })
  })

  assets.scripts.forEach((script) => {
    flat.push({
      id: script.id,
      campaign_id: campaignId,
      creative_type: 'script',
      platform: script.format,
      content: {
        format: script.format,
        label: script.format.replace(/_/g, ' '),
        duration_estimate: script.duration_estimate,
        content_preview: script.content.slice(0, 200),
      },
      validation_status: 'ai_draft',
      created_at: now,
      updated_at: null,
    })
  })

  assets.audio.forEach((audio) => {
    flat.push({
      id: audio.id,
      campaign_id: campaignId,
      creative_type: 'audio',
      platform: audio.format,
      content: {
        url: audio.url,
        duration_seconds: audio.duration_seconds,
        voice_style: audio.voice_style,
        label: audio.format.replace(/_/g, ' '),
      },
      validation_status: 'ai_draft',
      created_at: now,
      updated_at: null,
    })
  })

  return flat
}
```

- [ ] **Step 2: Add startup seeding at the bottom of `db/campaigns.ts`**

Add this block at the **very end** of `frontend/src/mocks/db/campaigns.ts` (after `export const campaignStore = ...` line):

```typescript
// Seed creativesStore from seed campaigns that already have creative_assets.
// Uses "don't overwrite" so existing localStorage values (with updated statuses) win.
function _seedCreativesFromInitial(): void {
  for (const [campaignId, campaign] of Object.entries(initialCampaigns)) {
    if (!campaign.creative_assets) continue
    for (const c of flattenCreativeAssets(campaignId, campaign.creative_assets)) {
      const id = c.id as string
      if (!creativesStore[id]) {
        creativesStore[id] = c
      }
    }
  }
}
_seedCreativesFromInitial()
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/mocks/db/campaigns.ts
git commit -m "feat(mock): add flattenCreativeAssets + seed creativesStore from initial campaigns"
```

---

## Task 2: Rewrite `mocks/handlers/creatives.ts` to use `creativesStore`

**Files:**
- Modify: `frontend/src/mocks/handlers/creatives.ts`

**Context:** Current file uses a hardcoded `MOCK_CREATIVES as const` array. `GET` always returns those 3 items. `PATCH /status` returns a new object but mutates nothing — lost on refresh. Replace entirely with reads/writes to `creativesStore` imported from `../db/campaigns`.

The `GET /creatives` handler must support `?campaign_id=X` filtering (used by `useCreatives(campaignId)`). The `PATCH /creatives/:id/status` body has `{ status: string; notes?: string }` — store as `validation_status` (backend canonical name) and also echo back as `status` so `BadgeStatus` (which reads `asset.status ?? asset.validation_status`) sees it immediately.

- [ ] **Step 1: Replace entire file**

Overwrite `frontend/src/mocks/handlers/creatives.ts` with:

```typescript
import { http, HttpResponse } from 'msw'
import { creativesStore } from '../db/campaigns'

export const creativesHandlers = [
  http.get('/api/v1/creatives', ({ request }) => {
    const campaignId = new URL(request.url).searchParams.get('campaign_id')
    const all = Object.values(creativesStore) as Record<string, unknown>[]
    const filtered = campaignId
      ? all.filter((c) => c.campaign_id === campaignId)
      : all
    return HttpResponse.json({ creatives: filtered, total: filtered.length })
  }),

  http.get('/api/v1/creatives/:id', ({ params }) => {
    const creative = creativesStore[params.id as string]
    if (!creative) return HttpResponse.json({ detail: 'Not found' }, { status: 404 })
    return HttpResponse.json(creative)
  }),

  http.patch('/api/v1/creatives/:id/status', async ({ params, request }) => {
    const id = params.id as string
    const creative = creativesStore[id] as Record<string, unknown> | undefined
    if (!creative) return HttpResponse.json({ detail: 'Not found' }, { status: 404 })
    const body = await request.json() as { status: string; notes?: string }
    const updated = {
      ...creative,
      validation_status: body.status,
      status: body.status,
      notes: body.notes ?? (creative.notes as string | null) ?? null,
      updated_at: new Date().toISOString(),
    }
    creativesStore[id] = updated
    return HttpResponse.json(updated)
  }),
]
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/mocks/handlers/creatives.ts
git commit -m "feat(mock): replace static MOCK_CREATIVES with persisted creativesStore"
```

---

## Task 3: Populate `creativesStore` in the `generate-creatives` campaign handler

**Files:**
- Modify: `frontend/src/mocks/handlers/campaigns.ts`

**Context:** The `generate-creatives` handler (around line 107) currently only writes `creative_assets` to `campaignStore`. It must also call `flattenCreativeAssets` and write each creative into `creativesStore` so they appear in Creative Studio immediately.

Also update the `review` handler (around line 139) to sync approval state back to `creativesStore` — so when a user approves an asset in the campaign view, it also shows the updated badge in Creative Studio.

- [ ] **Step 1: Import `flattenCreativeAssets` and `creativesStore`**

At the top of `frontend/src/mocks/handlers/campaigns.ts`, the existing import is:
```typescript
import * as db from '../db/campaigns'
```
This already gives access to `db.flattenCreativeAssets` and `db.creativesStore` — no import change needed.

- [ ] **Step 2: Update `generate-creatives` handler**

Find this block in `frontend/src/mocks/handlers/campaigns.ts`:

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
```

Replace with:

```typescript
  http.post('/api/v1/campaigns/:id/generate-creatives', ({ params }) => {
    const campaign = db.campaignStore[params.id as string]
    if (!campaign) return new HttpResponse(null, { status: 404 })
    const creative_assets = db.generateCreativeAssets(campaign.id)
    db.campaignStore[campaign.id] = {
      ...campaign,
      status: 'creative_ready',
      creative_assets,
      updated_at: new Date().toISOString(),
    }
    // Populate creativesStore so Creative Studio shows these immediately
    for (const c of db.flattenCreativeAssets(campaign.id, creative_assets)) {
      db.creativesStore[c.id as string] = c
    }
    return HttpResponse.json(db.campaignStore[campaign.id])
  }),
```

- [ ] **Step 3: Update the `review` handler to sync approval into `creativesStore`**

Find this block (the review handler ending around line 173):

```typescript
    db.campaignStore[campaign.id] = { ...campaign, creative_assets: assets, updated_at: new Date().toISOString() }
    return HttpResponse.json(db.campaignStore[campaign.id])
  }),
```

Replace with:

```typescript
    db.campaignStore[campaign.id] = { ...campaign, creative_assets: assets, updated_at: new Date().toISOString() }

    // Sync approval state into creativesStore so Creative Studio badge updates
    const newStatus = approved === true ? 'internal_approved' : approved === false ? 'revision_requested' : 'ai_draft'
    const existing = db.creativesStore[assetId] as Record<string, unknown> | undefined
    if (existing) {
      db.creativesStore[assetId] = {
        ...existing,
        validation_status: newStatus,
        status: newStatus,
        updated_at: new Date().toISOString(),
      }
    }

    return HttpResponse.json(db.campaignStore[campaign.id])
  }),
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/mocks/handlers/campaigns.ts
git commit -m "feat(mock): populate creativesStore on generate-creatives and sync review approval"
```

---

## Task 4: Tests

**Files:**
- Create: `frontend/src/test/creatives-persist.test.ts`

**Context:** Test `flattenCreativeAssets` as a pure function (no DOM needed). Verify it returns the right count, shapes, and IDs. Also verify the `GET /creatives` handler returns `creativesStore` contents (not the old hardcoded array) by checking the response shape includes `creatives` array with `campaign_id`.

- [ ] **Step 1: Create test file**

```typescript
// frontend/src/test/creatives-persist.test.ts
import { describe, it, expect, beforeEach } from 'vitest'
import { flattenCreativeAssets, creativesStore, generateCreativeAssets } from '@/mocks/db/campaigns'

describe('flattenCreativeAssets', () => {
  const assets = generateCreativeAssets('test-cam')
  const flat = flattenCreativeAssets('test-cam', assets)

  it('returns a flat array (one entry per sub-asset)', () => {
    const expected = assets.images.length + assets.copy.length + assets.scripts.length + assets.audio.length
    expect(flat.length).toBe(expected)
  })

  it('every item has campaign_id, creative_type, platform, content, validation_status', () => {
    for (const c of flat) {
      expect(c.campaign_id).toBe('test-cam')
      expect(typeof c.creative_type).toBe('string')
      expect(typeof c.platform).toBe('string')
      expect(c.content).toBeTruthy()
      expect(c.validation_status).toBe('ai_draft')
    }
  })

  it('image items have content.url', () => {
    const images = flat.filter((c) => c.creative_type === 'image')
    expect(images.length).toBeGreaterThan(0)
    for (const img of images) {
      expect((img.content as Record<string, unknown>).url).toBeTruthy()
    }
  })

  it('copy items have content.preview', () => {
    const copies = flat.filter((c) => c.creative_type === 'copy')
    expect(copies.length).toBeGreaterThan(0)
    for (const cp of copies) {
      expect(typeof (cp.content as Record<string, unknown>).preview).toBe('string')
    }
  })

  it('script items have content.content_preview and content.duration_estimate', () => {
    const scripts = flat.filter((c) => c.creative_type === 'script')
    expect(scripts.length).toBeGreaterThan(0)
    for (const sc of scripts) {
      const cnt = sc.content as Record<string, unknown>
      expect(typeof cnt.content_preview).toBe('string')
      expect(typeof cnt.duration_estimate).toBe('string')
    }
  })

  it('audio items have content.url and content.duration_seconds', () => {
    const audios = flat.filter((c) => c.creative_type === 'audio')
    expect(audios.length).toBeGreaterThan(0)
    for (const au of audios) {
      const cnt = au.content as Record<string, unknown>
      expect(typeof cnt.url).toBe('string')
      expect(typeof cnt.duration_seconds).toBe('number')
    }
  })

  it('copy items have unique ids (no id collision across campaigns)', () => {
    const flatA = flattenCreativeAssets('cam-A', assets)
    const flatB = flattenCreativeAssets('cam-B', assets)
    const idsA = new Set(flatA.map((c) => c.id as string))
    const idsB = new Set(flatB.map((c) => c.id as string))
    for (const id of idsB) {
      expect(idsA.has(id)).toBe(false)
    }
  })
})

describe('creativesStore seeded from initialCampaigns', () => {
  it('contains creatives for c-003 (seeded campaign with creative_assets)', () => {
    const c003Items = Object.values(creativesStore).filter(
      (c) => (c as Record<string, unknown>).campaign_id === 'c-003'
    )
    expect(c003Items.length).toBeGreaterThan(0)
  })

  it('contains creatives for c-004 (seeded campaign with creative_assets)', () => {
    const c004Items = Object.values(creativesStore).filter(
      (c) => (c as Record<string, unknown>).campaign_id === 'c-004'
    )
    expect(c004Items.length).toBeGreaterThan(0)
  })
})
```

- [ ] **Step 2: Run tests**

```bash
cd D:/staging/ntm/frontend
npx vitest run src/test/creatives-persist.test.ts
```

Expected: All 8 tests pass.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/test/creatives-persist.test.ts
git commit -m "test(mock): add flattenCreativeAssets + creativesStore seeding tests"
```

---

## Self-Review

**Spec coverage:**
- ✅ Generate creatives → appears in Creative Studio: Task 3, Step 2 (`generate-creatives` writes to `creativesStore`)
- ✅ Approve → status persists on refresh: Task 2 (`PATCH` writes `validation_status` back to `creativesStore`)
- ✅ Re-login → creatives still visible: `creativesStore` is `createPersistedStore` (localStorage), survives session
- ✅ c-003/c-004 seeded on first load: Task 1, Step 2 (`_seedCreativesFromInitial`)
- ✅ `GET /creatives?campaign_id=X` filtering: Task 2, Step 1 (filters `Object.values(creativesStore)`)
- ✅ `CreativeStudioPage` content fields match: `content` payloads shaped to match `ImageCard`, `CopyCard`, `ScriptCard` field access patterns

**Placeholder scan:** None.

**Type consistency:**
- `flattenCreativeAssets(campaignId, assets)` — same signature in Task 1 definition, Task 3 call, Task 4 test import ✓
- `creativesStore[id]` write pattern consistent across Task 2 (PATCH handler), Task 3 (generate-creatives), Task 1 (seeding) ✓
- `validation_status` field name consistent across all writers and `BadgeStatus` reader ✓
