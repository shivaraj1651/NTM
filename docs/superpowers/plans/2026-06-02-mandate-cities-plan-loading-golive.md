# Mandate Cities, Activation Plan Loading & Go Live Real Ads — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add city targeting to mandate form, fix activation plan loading UX, and make Go Live call Google/Meta Ads synchronously in real-time.

**Architecture:** Three independent frontend/backend changes sharing a single branch. Cities are a static lookup in `geography.ts`. Plan loading is fixed by keying off campaign status (not HTTP loading state). Go Live activation is made synchronous by replacing Celery dispatch with direct `await` calls in `digital_activator.py`.

**Tech Stack:** React 18, TypeScript, Zod, react-hook-form, TanStack Query, Vitest + React Testing Library, FastAPI, Python 3.12, httpx, Motor (MongoDB), MSW (test-only)

---

## Files Changed

| File | Action | Purpose |
|------|--------|---------|
| `frontend/src/lib/geography.ts` | Modify | Add `CITIES` const |
| `frontend/src/types/admin.ts` | Modify | Add `cities?: string[]` to 3 interfaces |
| `frontend/src/pages/Mandate/MandateFormPage.tsx` | Modify | Cities field + reset logic |
| `frontend/src/pages/Admin/Campaigns/PlanPage.tsx` | Modify | Status-driven loading state + gate table |
| `frontend/src/pages/Admin/Campaigns/GoLivePage.tsx` | Modify | Remove hardcoded test mode warning |
| `backend/app/routers/digital_activator.py` | Modify | Synchronous activation, remove Celery dispatch |
| `.env` | Modify | Add `NTM_ADS_TEST_MODE=1` |
| `frontend/src/test/mandates.test.tsx` | Modify | Tests for cities field |
| `frontend/src/test/campaigns.test.tsx` | Modify | Tests for plan loading + go live |
| `backend/app/routers/tests/test_digital_activator_router.py` | Modify | Test synchronous activation |

---

## Task 1: Add CITIES data to geography.ts

**Files:**
- Modify: `frontend/src/lib/geography.ts`

- [ ] **Step 1: Add CITIES const to geography.ts**

Replace the entire file with:

```typescript
export const REGIONS = {
  APAC: ['India', 'Singapore', 'Australia', 'Japan', 'South Korea', 'Thailand'],
  EMEA: ['UAE', 'UK', 'Germany', 'France', 'Saudi Arabia', 'South Africa'],
  Americas: ['USA', 'Canada', 'Brazil', 'Mexico', 'Colombia'],
} as const

export const CITIES: Record<string, string[]> = {
  // APAC
  India:       ['Mumbai', 'Delhi', 'Bangalore', 'Chennai', 'Hyderabad', 'Pune', 'Kolkata'],
  Singapore:   ['Singapore City', 'Jurong East', 'Woodlands', 'Tampines', 'Clementi'],
  Australia:   ['Sydney', 'Melbourne', 'Brisbane', 'Perth', 'Adelaide', 'Gold Coast'],
  Japan:       ['Tokyo', 'Osaka', 'Yokohama', 'Nagoya', 'Sapporo', 'Fukuoka'],
  'South Korea': ['Seoul', 'Busan', 'Incheon', 'Daegu', 'Daejeon', 'Gwangju'],
  Thailand:    ['Bangkok', 'Chiang Mai', 'Phuket', 'Pattaya', 'Khon Kaen'],
  // EMEA
  UAE:         ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'Ras Al Khaimah'],
  UK:          ['London', 'Manchester', 'Birmingham', 'Glasgow', 'Leeds', 'Liverpool'],
  Germany:     ['Berlin', 'Munich', 'Hamburg', 'Frankfurt', 'Cologne', 'Stuttgart'],
  France:      ['Paris', 'Lyon', 'Marseille', 'Toulouse', 'Nice', 'Nantes'],
  'Saudi Arabia': ['Riyadh', 'Jeddah', 'Mecca', 'Medina', 'Dammam', 'Khobar'],
  'South Africa': ['Johannesburg', 'Cape Town', 'Durban', 'Pretoria', 'Port Elizabeth'],
  // Americas
  USA:         ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia', 'Dallas'],
  Canada:      ['Toronto', 'Vancouver', 'Montreal', 'Calgary', 'Ottawa', 'Edmonton'],
  Brazil:      ['São Paulo', 'Rio de Janeiro', 'Brasília', 'Salvador', 'Fortaleza', 'Curitiba'],
  Mexico:      ['Mexico City', 'Guadalajara', 'Monterrey', 'Puebla', 'Tijuana', 'León'],
  Colombia:    ['Bogotá', 'Medellín', 'Cali', 'Barranquilla', 'Cartagena'],
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/geography.ts
git commit -m "feat(mandate): add CITIES lookup per country to geography.ts"
```

---

## Task 2: Add cities field to TypeScript types

**Files:**
- Modify: `frontend/src/types/admin.ts`

- [ ] **Step 1: Add `cities?: string[]` to three interfaces**

Find the `Mandate` interface (around line 140) and add `cities?: string[]` after the `countries` line:

```typescript
export interface Mandate {
  // ...existing fields...
  countries?: string[]
  cities?: string[]        // ← add this line
  // ...rest of fields...
}
```

Find `MandateCreate` interface (around line 174) and add after `countries`:

```typescript
export interface MandateCreate {
  // ...existing fields...
  countries: string[]
  cities?: string[]        // ← add this line
  // ...rest of fields...
}
```

Find `MandateSummaryCard` interface (around line 189) and add after `countries`:

```typescript
export interface MandateSummaryCard extends Mandate {
  // ...existing fields...
  countries: string[]
  cities?: string[]        // ← add this line
  // ...rest of fields...
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/types/admin.ts
git commit -m "feat(mandate): add cities field to Mandate, MandateCreate, MandateSummaryCard types"
```

---

## Task 3: Add cities field to MandateFormPage

**Files:**
- Modify: `frontend/src/pages/Mandate/MandateFormPage.tsx`

- [ ] **Step 1: Add CITIES import and update schema**

At the top of `MandateFormPage.tsx`, update the geography import:

```typescript
import { REGIONS, CITIES } from '@/lib/geography'
```

Update the Zod schema — add `cities` after `countries`:

```typescript
const schema = z
  .object({
    name: z.string().min(3, 'Must be at least 3 characters'),
    objective: z.enum(OBJECTIVE_VALUES),
    region: z.string().min(1, 'Region is required'),
    countries: z.array(z.string()).min(1, 'Select at least one country'),
    cities: z.array(z.string()).optional().default([]),   // ← add this line
    total_budget: z.number().min(10000, 'Budget must be at least 10,000'),
    currency: z.enum(CURRENCY_VALUES),
    start_date: z.string()
      .min(1, 'Start date is required')
      .refine((v) => !v || v >= todayISO(), { message: 'Start date cannot be in the past' }),
    end_date: z.string().min(1, 'End date is required'),
  })
  .refine((d) => !d.start_date || !d.end_date || d.end_date > d.start_date, {
    message: 'End date must be after start date',
    path: ['end_date'],
  })
```

Update `FormValues` type — it's derived from schema via `z.infer<typeof schema>` so no change needed there.

- [ ] **Step 2: Update defaultValues and watch**

In `useForm` defaultValues, add `cities: []`:

```typescript
const form = useForm<FormValues>({
  resolver: zodResolver(schema),
  defaultValues: {
    name: '',
    objective: 'awareness',
    region: '',
    countries: [],
    cities: [],          // ← add this line
    total_budget: 50000,
    currency: 'USD',
    start_date: '',
    end_date: '',
  },
})
```

Add watch for countries after `watchRegion`:

```typescript
const watchRegion = form.watch('region')
const watchCountries = form.watch('countries')
const watchCurrency = form.watch('currency')
const watchStartDate = form.watch('start_date')
```

- [ ] **Step 3: Update existing mandate reset to include cities**

In the `useEffect` that resets the form for edit mode, add `cities`:

```typescript
useEffect(() => {
  if (existingMandate) {
    form.reset({
      name: existingMandate.name,
      objective: existingMandate.objective,
      region: existingMandate.region,
      countries: existingMandate.countries,
      cities: existingMandate.cities ?? [],   // ← add this line
      total_budget: existingMandate.total_budget,
      currency: existingMandate.currency as typeof CURRENCY_VALUES[number],
      start_date: existingMandate.start_date,
      end_date: existingMandate.end_date,
    })
  }
}, [existingMandate, form])
```

- [ ] **Step 4: Update region onChange to also reset cities**

Find the region `Select` onValueChange and add `cities` reset:

```typescript
onValueChange={(val) => {
  field.onChange(val)
  form.setValue('countries', [])
  form.setValue('cities', [])    // ← add this line
}}
```

- [ ] **Step 5: Update countries onChange to prune deselected cities**

Find the countries checkbox `onChange` handler. Replace it:

```typescript
onChange={(e) => {
  const newCountries = e.target.checked
    ? [...field.value, country]
    : field.value.filter((c) => c !== country)
  field.onChange(newCountries)
  // Remove cities that belong to deselected country
  if (!e.target.checked) {
    const removedCities = CITIES[country] ?? []
    const currentCities = form.getValues('cities') ?? []
    form.setValue('cities', currentCities.filter((c) => !removedCities.includes(c)))
  }
}}
```

- [ ] **Step 6: Add Cities FormField after the Countries block**

Insert after the closing `)}` of the Countries `FormField` (after line ~241), before the Budget slider section:

```tsx
{/* Cities — shown when at least one country is selected */}
{watchCountries.length > 0 && (
  <FormField
    control={form.control}
    name="cities"
    render={({ field }) => (
      <FormItem>
        <FormLabel>Cities <span className="text-muted-foreground text-xs font-normal">(optional)</span></FormLabel>
        <div className="space-y-3">
          {watchCountries.map((country) => {
            const citiesForCountry = CITIES[country] ?? []
            if (citiesForCountry.length === 0) return null
            return (
              <div key={country}>
                <p className="text-xs font-medium text-muted-foreground mb-1">{country}</p>
                <div className="grid grid-cols-2 gap-2">
                  {citiesForCountry.map((city) => (
                    <label
                      key={city}
                      className="flex items-center gap-2 cursor-pointer text-sm"
                    >
                      <input
                        type="checkbox"
                        checked={(field.value ?? []).includes(city)}
                        onChange={(e) => {
                          const current = field.value ?? []
                          if (e.target.checked) {
                            field.onChange([...current, city])
                          } else {
                            field.onChange(current.filter((c) => c !== city))
                          }
                        }}
                        className="h-4 w-4 rounded border-gray-300"
                      />
                      {city}
                    </label>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
        <FormMessage />
      </FormItem>
    )}
  />
)}
```

- [ ] **Step 7: Run the frontend dev server and verify visually**

```bash
cd frontend && npm run dev
```

Navigate to a mandate form → select a region → check a country → confirm cities appear below. Uncheck the country → confirm its cities disappear from selection. This is manual verification only (no automated test for the full flow due to MSW + form complexity, tested in Task 4).

- [ ] **Step 8: Commit**

```bash
git add frontend/src/pages/Mandate/MandateFormPage.tsx
git commit -m "feat(mandate): add optional cities multi-select field after countries"
```

---

## Task 4: Test cities field in MandateFormPage

**Files:**
- Modify: `frontend/src/test/mandates.test.tsx`

- [ ] **Step 1: Write failing tests for the cities field**

Add a new `describe('MandateFormPage — cities')` block at the end of `mandates.test.tsx`:

```typescript
describe('MandateFormPage — cities', () => {
  it('does not show cities section before any country is selected', () => {
    renderWithProviders(<MandateFormPage />, {
      route: '/mandates/new',
      path: '/mandates/new',
      user: CAMPAIGN_MANAGER_USER,
    })
    expect(screen.queryByText('Cities')).not.toBeInTheDocument()
  })

  it('shows cities for a selected country', async () => {
    renderWithProviders(<MandateFormPage />, {
      route: '/mandates/new',
      path: '/mandates/new',
      user: CAMPAIGN_MANAGER_USER,
    })
    // Select APAC region
    const regionTrigger = screen.getByRole('combobox', { name: /region/i })
    fireEvent.click(regionTrigger)
    await waitFor(() => screen.getByText('APAC'))
    fireEvent.click(screen.getByText('APAC'))

    // Check India
    await waitFor(() => screen.getByLabelText('India'))
    fireEvent.click(screen.getByLabelText('India'))

    // Cities for India should appear
    await waitFor(() => {
      expect(screen.getByText('Cities')).toBeInTheDocument()
      expect(screen.getByLabelText('Mumbai')).toBeInTheDocument()
      expect(screen.getByLabelText('Delhi')).toBeInTheDocument()
    })
  })

  it('removes city checkboxes when their country is deselected', async () => {
    renderWithProviders(<MandateFormPage />, {
      route: '/mandates/new',
      path: '/mandates/new',
      user: CAMPAIGN_MANAGER_USER,
    })
    // Select APAC region
    const regionTrigger = screen.getByRole('combobox', { name: /region/i })
    fireEvent.click(regionTrigger)
    await waitFor(() => screen.getByText('APAC'))
    fireEvent.click(screen.getByText('APAC'))

    // Check India, then uncheck it
    await waitFor(() => screen.getByLabelText('India'))
    fireEvent.click(screen.getByLabelText('India'))
    await waitFor(() => screen.getByText('Mumbai'))
    fireEvent.click(screen.getByLabelText('India'))

    // Mumbai should disappear
    await waitFor(() => {
      expect(screen.queryByLabelText('Mumbai')).not.toBeInTheDocument()
    })
  })
})
```

- [ ] **Step 2: Run tests to verify they fail (cities section not yet visible)**

```bash
cd frontend && npx vitest run src/test/mandates.test.tsx --reporter=verbose
```

Expected: The two new tests that check for cities will FAIL with "Unable to find an accessible element..." because the cities field isn't rendered yet (actually it IS rendered now from Task 3, so these should PASS — if they fail, check that `watchCountries` is wired correctly).

- [ ] **Step 3: Run all mandate tests to ensure no regressions**

```bash
cd frontend && npx vitest run src/test/mandates.test.tsx --reporter=verbose
```

Expected: All tests PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/test/mandates.test.tsx
git commit -m "test(mandate): add cities field tests — appear/disappear with country selection"
```

---

## Task 5: Fix Activation Plan loading state in PlanPage

**Files:**
- Modify: `frontend/src/pages/Admin/Campaigns/PlanPage.tsx`

- [ ] **Step 1: Fix isGenerating condition and add loading UI**

Replace the `isGenerating` line and the early-return loading block. Find:

```tsx
const isGenerating = campaign?.status === 'confirmed' && planLoading
const activations = (planResult ?? campaign)?.activation_plan ?? []
```

Replace with:

```tsx
const isGenerating = campaign?.status === 'confirmed'
const activations = (planResult ?? campaign)?.activation_plan ?? []
```

Find the early-return block:

```tsx
if (isGenerating) {
  return <p className="text-muted-foreground text-sm">Generating activation plan…</p>
}
```

Replace with:

```tsx
if (isGenerating) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-4">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
      <div className="text-center">
        <p className="font-semibold text-base">Please wait, Activation Plan is Generating...</p>
        <p className="text-sm text-muted-foreground mt-1">This may take a few seconds.</p>
      </div>
    </div>
  )
}
```

Add `Loader2` to the existing imports from `lucide-react` at the top of the file. The current file doesn't import from lucide-react, so add:

```typescript
import { Loader2 } from 'lucide-react'
```

- [ ] **Step 2: Gate the table and Approve Budget on activations.length > 0**

Currently the table and button always render (showing "No activations." row when empty). Replace the entire `return (...)` block (lines 101–169 in the current file) with the version below. The table `<TableHeader>` and `<TableBody>` internals are unchanged — only the outer structure changes:

```tsx
return (
  <div>
    <h2 className="text-lg font-semibold mb-4">Activation Plan</h2>

    {activations.length === 0 ? (
      <div className="flex flex-col items-center justify-center py-16 gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <div className="text-center">
          <p className="font-semibold text-base">Please wait, Activation Plan is Generating...</p>
          <p className="text-sm text-muted-foreground mt-1">This may take a few seconds.</p>
        </div>
      </div>
    ) : (
      <>
        <div className="rounded-md border mb-6">
          <Table>
            <TableHeader>
              {table.getHeaderGroups().map((hg) => (
                <TableRow key={hg.id}>
                  {hg.headers.map((header) => (
                    <TableHead key={header.id}>
                      {flexRender(header.column.columnDef.header, header.getContext())}
                    </TableHead>
                  ))}
                </TableRow>
              ))}
            </TableHeader>
            <TableBody>
              {table.getRowModel().rows.map((row) => (
                <Fragment key={row.id}>
                  <TableRow>
                    {row.getVisibleCells().map((cell) => (
                      <TableCell key={cell.id}>
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </TableCell>
                    ))}
                  </TableRow>
                  {row.getIsExpanded() && (
                    <TableRow>
                      <TableCell colSpan={columns.length} className="p-0">
                        <div className="bg-muted/30 p-4 space-y-2 text-sm">
                          <div className="grid grid-cols-2 gap-2">
                            <div><span className="font-medium">Channel:</span> {row.original.sub_channel || row.original.channel || '—'}</div>
                            <div><span className="font-medium">Geography:</span> {row.original.geography || '—'}</div>
                            <div><span className="font-medium">Phase:</span> {row.original.phase || '—'}</div>
                            <div><span className="font-medium">Audience Segment:</span> {row.original.audience_segment || row.original.audience || '—'}</div>
                            <div><span className="font-medium">Placement:</span> {row.original.placement || '—'}</div>
                            <div><span className="font-medium">Format:</span> {row.original.format || '—'}</div>
                            <div><span className="font-medium">Frequency:</span> {(row.original as any).frequency || '—'}</div>
                            <div><span className="font-medium">CPM:</span> {row.original.estimated_cpm != null ? `$${row.original.estimated_cpm}` : '—'}</div>
                          </div>
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </Fragment>
              ))}
            </TableBody>
          </Table>
        </div>

        {approveBudget.isError && (
          <p className="text-destructive text-sm mb-2">Failed to approve budget. Please try again.</p>
        )}

        <Button onClick={handleApprove} disabled={approveBudget.isPending}>
          {approveBudget.isPending ? 'Approving…' : 'Approve Budget'}
        </Button>
      </>
    )}
  </div>
)
```

The `isGenerating` early return stays as the first guard (campaign.status === 'confirmed'). The `activations.length === 0` guard inside this return handles the edge case where status is 'planned' but activation_plan somehow arrived empty.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Admin/Campaigns/PlanPage.tsx
git commit -m "feat(plan): fix loading state to show spinner+message while activation plan generates"
```

---

## Task 6: Test Activation Plan loading state

**Files:**
- Modify: `frontend/src/test/campaigns.test.tsx`

- [ ] **Step 1: Add tests for PlanPage loading states**

Find the existing PlanPage describe block in `campaigns.test.tsx`. Add these tests:

```typescript
describe('PlanPage — loading states', () => {
  it('shows generating spinner when campaign status is confirmed', async () => {
    server.use(
      http.get('/api/v1/campaigns/:id', () =>
        HttpResponse.json({
          id: 'c-001', mandate_id: 'm-001', tenant_id: 't1',
          status: 'confirmed',
          concepts: [], selected_concept_id: null,
          activation_plan: [], budget_proposal: null,
          creative_assets: null, kpi_configs: [],
          created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
        })
      ),
      http.get('/api/v1/campaigns/:id/activation-plan', () =>
        HttpResponse.json({
          id: 'c-001', status: 'confirmed', activation_plan: [],
        })
      ),
    )
    renderCampaignPage(PlanPage, 'c-001')
    await waitFor(() => {
      expect(screen.getByText('Please wait, Activation Plan is Generating...')).toBeInTheDocument()
    })
    expect(screen.queryByText('Approve Budget')).not.toBeInTheDocument()
  })

  it('shows table and Approve Budget when activations arrive', async () => {
    server.use(
      http.get('/api/v1/campaigns/:id', () =>
        HttpResponse.json({
          id: 'c-001', mandate_id: 'm-001', tenant_id: 't1',
          status: 'planned',
          concepts: [], selected_concept_id: null,
          activation_plan: [
            {
              id: 'act-1', channel: 'Google Ads', sub_channel: 'Search',
              geography: 'India', phase: 'Phase 1',
              estimated_reach: 50000, cost_estimated: 10000,
            },
          ],
          budget_proposal: null, creative_assets: null, kpi_configs: [],
          created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
        })
      ),
    )
    renderCampaignPage(PlanPage, 'c-001')
    await waitFor(() => {
      expect(screen.getByText('Approve Budget')).toBeInTheDocument()
      expect(screen.getByText('Google Ads')).toBeInTheDocument()
    })
    expect(screen.queryByText('Please wait, Activation Plan is Generating...')).not.toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run tests**

```bash
cd frontend && npx vitest run src/test/campaigns.test.tsx --reporter=verbose
```

Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/test/campaigns.test.tsx
git commit -m "test(plan): add loading state tests for PlanPage"
```

---

## Task 7: Remove hardcoded test mode warning from GoLivePage

**Files:**
- Modify: `frontend/src/pages/Admin/Campaigns/GoLivePage.tsx`

- [ ] **Step 1: Remove the hardcoded warning block**

Find and delete this entire block in `GoLivePage.tsx` (around lines 292-304):

```tsx
{/* Test mode notice */}
<div className="flex items-start gap-2 rounded-md border border-amber-300 bg-amber-50 p-3 text-xs text-amber-800">
  <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
  <div>
    <p className="font-semibold">Developer Test Mode active (NTM_ADS_TEST_MODE=1)</p>
    <p className="mt-0.5">
      Real API calls will be made to Google Ads and Meta Ads.
      Campaigns are created as <strong>PAUSED</strong> with a [TEST] prefix — no budget will be spent.
      Disable NTM_ADS_TEST_MODE to launch live.
    </p>
  </div>
</div>
```

Also remove the `AlertTriangle` import if it is no longer used anywhere else in the file. Check the other imports and remove unused ones:

```typescript
// Remove AlertTriangle from the lucide-react import line if only used in the deleted block
import {
  Loader2, CheckCircle2, XCircle, Clock, ExternalLink,
  Rocket, FlaskConical,    // ← AlertTriangle removed
} from 'lucide-react'
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Admin/Campaigns/GoLivePage.tsx
git commit -m "fix(golive): remove hardcoded test mode warning — actual mode shown from activation_results"
```

---

## Task 8: Enable test mode in .env

**Files:**
- Modify: `.env`

- [ ] **Step 1: Add NTM_ADS_TEST_MODE=1**

Open `.env` and add after the `# ── Platform APIs ──` section, before `GOOGLE_ADS_DEVELOPER_TOKEN`:

```env
# ── Ad Platform Mode ─────────────────────────────────────────────────────────
NTM_ADS_TEST_MODE=1
# Set to 0 or remove to launch real campaigns with budget spend
```

This causes `activate_google` and `activate_meta` to create campaigns with:
- Status: PAUSED (no spend)
- Name prefix: [TEST]
- Real platform IDs returned — verifiable in Google Ads Manager and Meta Ads Manager.

- [ ] **Step 2: Commit**

```bash
git add .env
git commit -m "chore(env): enable NTM_ADS_TEST_MODE for safe real-API testing"
```

---

## Task 9: Make /activate endpoint synchronous

**Files:**
- Modify: `backend/app/routers/digital_activator.py`

- [ ] **Step 1: Write the failing test first**

Check the existing test file:
```bash
cat backend/app/routers/tests/test_digital_activator_router.py
```

Add a test that expects `activation_results` in the response body. Append to the existing test file:

```python
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient


@pytest.mark.anyio
async def test_activate_returns_results_synchronously(async_client: AsyncClient, auth_headers: dict):
    """POST /campaigns/:id/activate should return activation_results immediately."""
    campaign_id = "test-campaign-sync"

    # Pre-seed a campaign document in the test DB with activation_plan
    # (Assumes async_client fixture has the test app with a real MongoDB connection)
    # We patch the tool functions to avoid real API calls in tests
    fake_google_result = {
        "campaign_id": "google-test-123",
        "ad_id": "ad-test-456",
        "status": "test_live",
        "test_mode": True,
        "error": None,
    }
    fake_meta_result = {
        "campaign_id": "meta-test-789",
        "ad_set_id": "adset-test-001",
        "ad_id": "ad-test-002",
        "status": "test_live",
        "test_mode": True,
        "error": None,
    }

    with (
        patch("backend.app.routers.digital_activator.activate_google", new_callable=AsyncMock, return_value=fake_google_result),
        patch("backend.app.routers.digital_activator.activate_meta", new_callable=AsyncMock, return_value=fake_meta_result),
    ):
        response = await async_client.post(
            f"/api/v1/campaigns/{campaign_id}/activate",
            headers=auth_headers,
        )

    # 202 accepted, results present
    assert response.status_code == 202
    body = response.json()
    assert "campaign_id" in body
    assert "activation_results" in body
```

Run to confirm FAIL:

```bash
cd backend && python -m pytest app/routers/tests/test_digital_activator_router.py -v -k "test_activate_returns_results"
```

Expected: FAIL — `activation_results` not in response body (current response is `JobQueuedResponse` with no such field).

- [ ] **Step 2: Rewrite digital_activator.py with synchronous activation**

Replace the entire content of `backend/app/routers/digital_activator.py` with:

```python
# backend/app/routers/digital_activator.py
import logging
import os
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pydantic import BaseModel

from backend.app.core.dependencies import get_current_tenant, require_role
from backend.app.core.models import User, UserRole
from backend.app.services.campaign_service import CampaignService
from backend.app.tools.google_ads import activate_google
from backend.app.tools.meta_ads import activate_meta
from backend.app.tools.linkedin_ads import activate_linkedin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["digital-activator"])

DIGITAL_ROLES = [
    UserRole.CAMPAIGN_MANAGER,
    UserRole.TENANT_ADMIN,
    UserRole.PLATFORM_ADMIN,
]

_GOOGLE_KEYWORDS = ("google", "search", "display", "youtube", "video", "programmatic", "gdn")
_META_KEYWORDS = ("meta", "facebook", "instagram", "social", "reels", "stories")
_LINKEDIN_KEYWORDS = ("linkedin",)


class ActivationResponse(BaseModel):
    job_id: str
    campaign_id: str
    activation_results: dict


def _channel_to_platform(channel_enum: str | None, channel: str | None) -> str | None:
    if channel_enum:
        lower = channel_enum.lower()
        if lower in ("google_ads", "meta_ads", "linkedin_ads"):
            return lower
        if any(k in lower for k in _GOOGLE_KEYWORDS):
            return "google_ads"
        if any(k in lower for k in _META_KEYWORDS):
            return "meta_ads"
        if any(k in lower for k in _LINKEDIN_KEYWORDS):
            return "linkedin_ads"
    if channel:
        lower = channel.lower()
        if any(k in lower for k in _GOOGLE_KEYWORDS):
            return "google_ads"
        if any(k in lower for k in _META_KEYWORDS):
            return "meta_ads"
        if any(k in lower for k in _LINKEDIN_KEYWORDS):
            return "linkedin_ads"
    return None


async def get_db() -> AsyncIOMotorDatabase:
    mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    mongo_db_name = os.getenv("MONGODB_DB", "ntm")
    client = AsyncIOMotorClient(mongo_url)
    return client[mongo_db_name]


@router.post("/campaigns/{campaign_id}/activate", response_model=ActivationResponse, status_code=202)
async def activate_campaign(
    campaign_id: str,
    _: User = Depends(require_role(DIGITAL_ROLES)),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ActivationResponse:
    svc = CampaignService(db)
    campaign = await svc.get(campaign_id, tenant_id)
    campaign_dict = campaign if isinstance(campaign, dict) else campaign.model_dump()

    activation_plan = campaign_dict.get("activation_plan") or []

    # Extract creative URL (prefer landscape image)
    creative_assets = campaign_dict.get("creative_assets") or {}
    images = creative_assets.get("images") or []
    landscape = next((i for i in images if i.get("format") == "landscape"), None)
    creative_url = (landscape or (images[0] if images else {})).get("url", "")

    # Extract selected concept for ad copy
    concepts = campaign_dict.get("concepts", [])
    selected_id = campaign_dict.get("selected_concept_id")
    concept = next(
        (c for c in concepts if str(c.get("id", "")) == selected_id),
        concepts[0] if concepts else {},
    )
    tone_board = concept.get("tone_board", {}) if isinstance(concept.get("tone_board"), dict) else {}
    messaging = concept.get("message_architecture", {}) if isinstance(concept.get("message_architecture"), dict) else {}

    base_platform_config = {
        "tagline":        concept.get("tagline", ""),
        "master_message": messaging.get("master_message", ""),
        "concept_name":   concept.get("name", ""),
        "description":    tone_board.get("visual_direction", "") or messaging.get("master_message", ""),
        "objective":      campaign_dict.get("mandate", {}).get("objective", "awareness"),
        "geo_locations":  {"countries": ["US"]},
    }

    # Aggregate budget per platform
    platform_budgets: dict[str, float] = {}
    platform_activations: dict[str, dict] = {}
    for act in activation_plan:
        act_dict = dict(act) if isinstance(act, dict) else act.model_dump()
        platform = _channel_to_platform(
            act_dict.get("channel_enum") or act_dict.get("channelEnum"),
            act_dict.get("channel"),
        )
        if platform:
            cost = float(act_dict.get("cost_estimated") or act_dict.get("budget") or 0)
            platform_budgets[platform] = platform_budgets.get(platform, 0) + cost
            if platform not in platform_activations:
                platform_activations[platform] = act_dict

    # Default split if no recognised platform channels
    if not platform_activations and activation_plan:
        total_budget = sum(
            float((dict(a) if isinstance(a, dict) else a.model_dump()).get("cost_estimated") or 0)
            for a in activation_plan
        )
        base_name = base_platform_config["concept_name"] or f"Campaign {campaign_id[:8]}"
        platform_activations["google_ads"] = {
            "id": str(uuid4()), "name": base_name,
            "cost_estimated": total_budget * 0.5, "channel": "Google Ads Search",
        }
        platform_activations["meta_ads"] = {
            "id": str(uuid4()), "name": base_name,
            "cost_estimated": total_budget * 0.5, "channel": "Meta Ads",
        }
        platform_budgets["google_ads"] = total_budget * 0.5
        platform_budgets["meta_ads"]   = total_budget * 0.5

    # ── Activate each platform synchronously ──────────────────────────────────
    final_results: dict[str, dict] = {}

    for platform, act_payload in platform_activations.items():
        if "id" not in act_payload or not act_payload["id"]:
            act_payload["id"] = str(uuid4())
        act_payload["cost_estimated"] = platform_budgets.get(platform, act_payload.get("cost_estimated", 0))

        logger.info("Activating %s synchronously budget=%.0f campaign=%s", platform, act_payload["cost_estimated"], campaign_id)

        if platform == "google_ads":
            result = await activate_google(act_payload, base_platform_config, creative_url)
        elif platform == "meta_ads":
            result = await activate_meta(act_payload, base_platform_config, creative_url)
        elif platform == "linkedin_ads":
            result = await activate_linkedin(act_payload, base_platform_config, creative_url)
        else:
            result = {"status": "failed", "error": f"Unknown platform: {platform}"}

        final_results[platform] = result
        logger.info("Platform %s result: status=%s campaign_id=%s", platform, result.get("status"), result.get("campaign_id"))

    # Write results to MongoDB so campaign GET returns them
    if final_results:
        try:
            await db["campaigns"].update_one(
                {"_id": campaign_id, "tenant_id": tenant_id},
                {"$set": {
                    "activation_results": final_results,
                    "updated_at": datetime.now(UTC).isoformat(),
                }},
            )
        except Exception as exc:
            logger.warning("Failed to write activation_results to MongoDB: %s", exc)

    if not final_results:
        logger.warning("No platforms activated for campaign %s", campaign_id)

    return ActivationResponse(
        job_id=str(uuid4()),
        campaign_id=campaign_id,
        activation_results=final_results,
    )
```

- [ ] **Step 3: Run the test**

```bash
cd backend && python -m pytest app/routers/tests/test_digital_activator_router.py -v -k "test_activate_returns_results"
```

Expected: PASS — `activation_results` present in response body with mocked platform results.

- [ ] **Step 4: Run full backend tests to check for regressions**

```bash
cd backend && python -m pytest app/routers/tests/test_digital_activator_router.py -v
```

Expected: All tests PASS. If any existing test imports `platform_activate_google` from this file, update it to import from `backend.app.tasks.activation_tasks` instead (Celery tasks still exist there).

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/digital_activator.py
git commit -m "feat(golive): synchronous ad activation — direct await instead of Celery dispatch"
```

---

## Task 10: Final integration check and test run

- [ ] **Step 1: Run all frontend tests**

```bash
cd frontend && npx vitest run --reporter=verbose
```

Expected: All tests PASS. No regressions.

- [ ] **Step 2: Run all backend tests**

```bash
cd backend && python -m pytest --tb=short -q
```

Expected: All tests PASS.

- [ ] **Step 3: Start the backend and test Go Live end-to-end**

```bash
cd backend && uvicorn backend.app.main:app --reload --port 8000
```

In a second terminal:
```bash
cd frontend && npm run dev
```

Walk the full campaign cycle to Go Live:
1. Create/select a mandate
2. Create a campaign → concepts appear
3. Select a concept → Confirm → Navigate to Plan tab
4. Verify "Please wait, Activation Plan is Generating..." spinner shows
5. Wait for plan to load → verify table appears with Approve Budget button
6. Approve Budget → proceed through creatives
7. On Go Live page: verify the hardcoded amber warning is GONE
8. Click Launch Campaign → verify platform cards appear with `test_live` status and real campaign IDs
9. Check Google Ads Manager (`ads.google.com`) for a `[TEST]` campaign
10. Check Meta Ads Manager for a `[TEST]` campaign

- [ ] **Step 4: Final commit**

```bash
git add .
git commit -m "chore: final integration — mandate cities, plan loading, synchronous go-live"
```
