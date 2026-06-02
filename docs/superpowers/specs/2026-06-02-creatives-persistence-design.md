# Creatives Persistence — Creative Studio Fix

**Date:** 2026-06-02  
**Status:** Approved

## Problem

Creative Studio shows 3 hardcoded assets that never update and reset on refresh. Three bugs:
1. `creativesStore` (line 53, `db/campaigns.ts`) exists but is empty — nothing reads or writes it
2. `mocks/handlers/creatives.ts` uses a `MOCK_CREATIVES` const — PATCH mutations are lost on reload
3. `generate-creatives` campaign handler never populates `creativesStore` — generated assets never appear in Creative Studio

## Solution: Fix MSW mock layer, make `creativesStore` the single source of truth

### Shape: `Creative` (flat, stored per-id in `creativesStore`)

```ts
{
  id: string               // e.g. "c-003-img-1"
  campaign_id: string
  creative_type: string    // 'image' | 'copy' | 'script' | 'audio'
  platform: string         // format/sub-type e.g. 'square', 'social_caption'
  content: Record<string, unknown>  // asset-type-specific payload
  validation_status: string         // 'ai_draft' | 'internal_approved' | 'client_approved' | 'revision_requested'
  created_at: string
  updated_at: string
}
```

### Helper: `flattenCreativeAssets(campaignId, assets) → Creative[]`

Converts `CreativeAssets` (nested `{ copy, scripts, images, audio }`) to flat `Creative[]`:
- Each `ImageAsset` → `{ creative_type: 'image', platform: img.format, content: { url, label, ... } }`
- Each `CopyAsset` → `{ creative_type: 'copy', platform: copy.asset_type, content: { variants, ... } }`
- Each `ScriptAsset` → `{ creative_type: 'script', platform: script.format, content: { ... } }`
- Each `AudioAsset` → `{ creative_type: 'audio', platform: audio.format, content: { url, duration_seconds, ... } }`

IDs derived from existing sub-asset IDs where present, or generated as `${campaignId}-${type}-${index}`.

### Startup seeding

At module load time in `db/campaigns.ts`, iterate `initialCampaigns` — for any campaign with `creative_assets`, call `flattenCreativeAssets` and write each creative into `creativesStore` if not already present (merge, don't overwrite existing).

### Handler changes

**`mocks/handlers/creatives.ts`** — replace `MOCK_CREATIVES`:
- `GET /creatives` → `Object.values(creativesStore)`, filter by `campaign_id` query param if present
- `GET /creatives/:id` → `creativesStore[id]`
- `PATCH /creatives/:id/status` → `creativesStore[id] = { ...existing, validation_status: body.status, updated_at: now }`

**`mocks/handlers/campaigns.ts`** — in `generate-creatives` handler:
- After writing `creative_assets` to `campaignStore`, call `flattenCreativeAssets` and write each into `creativesStore`

## Files Changed

| File | Change |
|------|--------|
| `frontend/src/mocks/db/campaigns.ts` | Add `flattenCreativeAssets()` helper; seed `creativesStore` from `initialCampaigns` at startup |
| `frontend/src/mocks/handlers/creatives.ts` | Replace static `MOCK_CREATIVES` with `creativesStore` reads/writes |
| `frontend/src/mocks/handlers/campaigns.ts` | After `generate-creatives`, populate `creativesStore` |

## Success Criteria

- Generate creatives on any campaign → appears immediately in Creative Studio tab
- Approve/reject a creative → status badge persists after page refresh
- Re-login → creatives still visible (localStorage survives session)
- Seed campaigns c-003, c-004 (already have assets) → show in Creative Studio on first load
- `GET /creatives?campaign_id=X` → returns only that campaign's creatives
