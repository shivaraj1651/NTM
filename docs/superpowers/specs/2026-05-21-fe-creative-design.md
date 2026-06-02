# fe-creative: Creative Studio Design

**Date:** 2026-05-21
**Scope:** Enhance `CreativesPage.tsx` with two-stage review workflow (internal → client), revision tracking, and asset lock. `Campaign.status` is NOT modified.

---

## Context

`CreativesPage.tsx` is fully built for internal asset generation and basic approve/reject.
Missing: the PRD two-stage review flow, revision cycle limit, comment on change request, and final lock.

---

## Key Constraint: CreativeStage is Separate from Campaign.status

`Campaign.status` stays at `creative_ready` throughout the entire review lifecycle.
Review stage is tracked as a separate field: `creative_assets.stage: CreativeStage`.

```typescript
type CreativeStage = 'internal_review' | 'client_review' | 'locked'
```

This field lives on the `creative_assets` object returned by `GET /api/v1/campaigns/:id`.
Backend stores it in MongoDB on the `creative_assets` subdocument, not on the top-level campaign document.

---

## Review Flow

```
Campaign status: creative_ready (stays here throughout)

creative_assets.stage:
  internal_review
        ↓  (NTM team reviews; all assets approved internally)
  client_review
        ↓  (client approves or requests change; max 2 revision cycles)
  locked
        (all assets approved by client; no further edits)
```

Up to 2 revision cycles are allowed in `client_review`. After 2, `Request Change` is disabled.

---

## Files Modified

- `frontend/src/pages/Admin/Campaigns/CreativesPage.tsx` — primary changes
- `frontend/src/types/admin.ts` — new types
- `frontend/src/hooks/useCampaigns.ts` — new mutations
- `frontend/src/mocks/handlers/campaigns.ts` — new endpoints
- `frontend/src/mocks/db/campaigns.ts` — stage field on mock data

---

## New Types (`admin.ts`)

```typescript
type CreativeStage = 'internal_review' | 'client_review' | 'locked'
type ReviewAction = 'approve' | 'request_change' | 'reject'

interface AssetReview {
  action: ReviewAction
  comment?: string          // required when action === 'request_change'
  revision_count: number    // 0, 1, or 2
  approved: boolean | null
}
```

`creative_assets` shape gains `stage: CreativeStage` at the top level.
Each asset gains `revision_count: number` alongside the existing `approved: boolean | null`.

---

## UI Components Added to CreativesPage.tsx

### StageBanner
Top-of-page strip showing current stage with label and CTA:

| Stage | Label | CTA |
|-------|-------|-----|
| `internal_review` | "Internal Review" | "Send to Client" button → advances to `client_review` |
| `client_review` | "Client Review" | none (stage advances automatically when all assets approved) |
| `locked` | "Approved & Locked" | none |

When `stage === 'locked'`, entire page is read-only.

### ReviewActions (replaces ApproveButtons)
Three-button group per asset:

- **Approve** (green check) — sets `approved: true`
- **Request Change** (yellow pencil) — opens `CommentDialog`, required comment, increments `revision_count`
- **Reject** (red X) — sets `approved: false`

In `internal_review` stage: all three actions available.
In `client_review` stage: all three actions available, but `Request Change` disabled if `revision_count >= 2`.
In `locked` stage: no actions shown.

### CommentDialog
Modal triggered by "Request Change":
- Single `<textarea>` (required, min 10 chars)
- "Send" button submits review action + comment
- "Cancel" dismisses without action

---

## New Mock Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/campaigns/:id/creatives/stage` | Advance stage (`internal_review` → `client_review`) |
| POST | `/api/v1/campaigns/:id/creatives/:kind/:assetId/review` | Submit review action (approve / request_change / reject) with optional comment |

---

## New Hooks (`useCampaigns.ts`)

```typescript
useAdvanceCreativeStage(campaignId: string)  // POST /creatives/stage
useReviewAsset(campaignId: string)           // POST /creatives/:kind/:assetId/review
```

Existing `useApproveCreativeAsset` is replaced by `useReviewAsset`.

---

## Auto-Lock Logic (frontend)

When `stage === 'client_review'` and every asset across all tabs has `approved === true`, the frontend calls `POST /creatives/stage` automatically to advance to `locked`. No manual button.

---

## Testing

- Existing tests for `CreativesPage` remain valid (generate, approve, regenerate paths)
- New test cases added to `frontend/src/test/campaigns.test.tsx`:
  - Stage banner renders correct label per stage
  - "Send to Client" advances stage
  - "Request Change" opens CommentDialog, requires comment
  - `revision_count >= 2` disables Request Change
  - `locked` stage renders no action buttons
  - Auto-lock fires when all assets approved in client_review

---

## What Does NOT Change

- `Campaign.status` field — untouched
- `useApproveCreativeAsset` existing hook — removed and replaced by `useReviewAsset`
- Regenerate functionality — unchanged
- Tab structure (Copy / Scripts / Images / Audio) — unchanged
