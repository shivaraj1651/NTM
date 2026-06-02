# TASK-023 Frontend: Onboarding + Mandate Module Design

**Date:** 2026-05-18  
**Stack:** React 18, TypeScript, Tailwind CSS, shadcn/ui, React Hook Form, Zod, React Query

---

## 1. Scope

Two new page groups, module-scoped to:
- `frontend/src/pages/Onboarding/` — standalone wizard, no AdminLayout
- `frontend/src/pages/Mandate/` — inside AdminLayout, new sidebar nav item

---

## 2. Architecture & Routes

```
/onboarding                        standalone (no sidebar)
  OnboardingPage (5-step wizard)

/admin/mandates                    AdminLayout + sidebar nav
  MandatesPage (list)
/admin/mandates/new
  MandateFormPage (create)
/admin/mandates/:id/edit
  MandateFormPage (edit, pre-populated)
/admin/mandates/:id/summary
  MandateSummaryPage (readonly + confirm/reject)
```

**Sidebar addition:**
```ts
{ label: 'Mandates', to: '/admin/mandates', icon: FileText }
```

---

## 3. Onboarding Wizard

### 3.1 Approach

Client-side state wizard (Approach B). Single route `/onboarding`. Step index held in component state. No URL changes per step. On completion → redirect to `/admin/mandates/new`.

### 3.2 Steps

| # | Component | Fields | Validation |
|---|-----------|--------|------------|
| 1 | `OrgInfoStep` | org_name (text), industry (select) | required, org_name min 2 chars |
| 2 | `LogoStep` | logo (file, image/*) | required, max 5 MB |
| 3 | `BrandGuidelinesStep` | brand_guidelines (file, application/pdf) | required, max 20 MB |
| 4 | `CompetitorsStep` | competitors (dynamic add/remove text list) | min 1 entry |
| 5 | `ReviewStep` | readonly summary of all collected data | — |

**Industry options (static):**
FMCG, Retail, Finance, Healthcare, Technology, Automotive, Entertainment, Telecom

### 3.3 Data Flow

- Each step owns a `useForm` instance with a Zod schema scoped to its fields.
- Parent `OnboardingPage` holds accumulated state across steps.
- On `ReviewStep` submit: assemble `FormData`, POST to `POST /api/v1/clients` (multipart).
- On success → `navigate('/admin/mandates/new', { state: { client_id } })`.

### 3.4 Progress Indicator

Top stepper bar with step numbers and labels. Completed steps marked with a checkmark. Current step highlighted.

### 3.5 Layout

Full-screen centered card. No sidebar. Steps take up a constrained 600px max-width column.

---

## 4. Mandate Form

### 4.1 Component

`pages/Mandate/MandateFormPage.tsx` — shared for create and edit.
- Create: receives `client_id` from router state.
- Edit: fetches mandate by `:id`, pre-populates form.

### 4.2 Fields & Validation

| Field | UI Control | Type | Validation |
|-------|-----------|------|------------|
| name | text input | string | required, min 3 chars |
| objective | `<Select>` | MandateObjective enum | required |
| region | `<Select>` | string | required |
| countries | checkbox group (filtered by region) | string[] | min 1 selected |
| total_budget | range slider + number input | number | required, > 0 |
| currency | `<Select>` | string | required |
| start_date | date input | ISO string | required |
| end_date | date input | ISO string | required, after start_date |

**Objective values:** `awareness | consideration | conversion | loyalty | engagement`

**Currency options:** USD, EUR, GBP, INR, AED

**Budget slider:** min 10,000 — max 10,000,000, step 10,000. Paired with a numeric input for precision entry.

### 4.3 Geography Static Data

Extracted to `frontend/src/lib/geography.ts`:

```ts
export const REGIONS: Record<string, string[]> = {
  APAC: ['India', 'Singapore', 'Australia', 'Japan', 'South Korea', 'Thailand'],
  EMEA: ['UAE', 'UK', 'Germany', 'France', 'Saudi Arabia', 'South Africa'],
  Americas: ['USA', 'Canada', 'Brazil', 'Mexico', 'Colombia'],
}
```

Region `<Select>` renders keys; country checkboxes render `REGIONS[selectedRegion]`.

### 4.4 Layout

Single scrollable form. No tabs. Submit button at bottom. On successful create → redirect to `/admin/mandates/:id/summary`. On edit submit → redirect to `/admin/mandates/:id/summary`.

---

## 5. Mandate Summary Card

### 5.1 Component

`pages/Mandate/MandateSummaryPage.tsx`. Fetches `GET /api/v1/mandates/:id/summary-card`. Readonly display.

### 5.2 Card Layout

```
┌─────────────────────────────────────────┐
│  [name]                    [status badge]│
│  Objective: [objective]                  │
│  Geography: [region] → [country list]   │
│  Budget: [currency] [total_budget]       │
│  Duration: [start_date] → [end_date]    │
│  Client: [org_name]  Industry: [industry]│
│  Competitors: [tag list]                 │
├─────────────────────────────────────────┤
│              [Reject]  [Confirm →]       │
└─────────────────────────────────────────┘
```

### 5.3 Confirm Flow

1. `POST /api/v1/mandates/:id/confirm`
2. On success → `POST /api/v1/campaigns` with `{ mandate_id: id }`
3. Navigate to `/admin/campaigns/:newCampaignId`

### 5.4 Reject Flow

Navigate to `/admin/mandates/:id/edit`. No API call.

### 5.5 States

- Loading: skeleton placeholders
- Error: toast notification
- Confirmed: buttons disabled, status badge shows `confirmed`

---

## 6. API Layer

### 6.1 New Types (`frontend/src/types/admin.ts`)

```ts
export type MandateObjective =
  | 'awareness' | 'consideration' | 'conversion' | 'loyalty' | 'engagement'

export type MandateStatus = 'draft' | 'pending_review' | 'confirmed' | 'rejected'

export interface ClientProfile {
  id: string
  org_name: string
  industry: string
  logo_url: string
  brand_guidelines_url: string
  competitors: string[]
  tenant_id: string
  created_at: string
}

export interface MandateCreate {
  name: string
  objective: MandateObjective
  region: string
  countries: string[]
  total_budget: number
  currency: string
  start_date: string
  end_date: string
  client_id: string
}

export interface MandateSummaryCard extends Mandate {
  objective: MandateObjective
  region: string
  countries: string[]
  start_date: string
  end_date: string
  status: MandateStatus
  client: ClientProfile
}
```

### 6.2 New API Functions (`frontend/src/api/admin.ts`)

```ts
createClient(formData: FormData)           // POST /api/v1/clients (multipart)
createMandate(payload: MandateCreate)      // POST /api/v1/mandates
getMandate(id: string)                     // GET /api/v1/mandates/:id
getMandateSummaryCard(id: string)          // GET /api/v1/mandates/:id/summary-card
confirmMandate(id: string)                 // POST /api/v1/mandates/:id/confirm
updateMandate(id: string, payload: Partial<MandateCreate>)  // PATCH /api/v1/mandates/:id
```

> `getMandates(tenantId)` already exists in `api/admin.ts`.

### 6.3 New Hooks (`frontend/src/hooks/useMandates.ts`)

```ts
useCreateClient()        // mutation → createClient
useMandateList(tenantId) // query → getMandates; named useMandateList (not useMandates)
                         // to avoid collision with useMandates() in useCampaigns.ts
useCreateMandate()       // mutation → createMandate
useMandateSummary(id)    // query → getMandateSummaryCard
useConfirmMandate(id)    // mutation → confirmMandate then createCampaign chain
useUpdateMandate(id)     // mutation → updateMandate
```

---

## 7. File Map

```
frontend/src/
  lib/
    geography.ts                       NEW — static region/country data
  types/
    admin.ts                           MODIFY — add new interfaces
  api/
    admin.ts                           MODIFY — add new API functions
  hooks/
    useMandates.ts                     NEW — mandate + client hooks
  pages/
    Onboarding/
      OnboardingPage.tsx               NEW — wizard shell
      OrgInfoStep.tsx                  NEW
      LogoStep.tsx                     NEW
      BrandGuidelinesStep.tsx          NEW
      CompetitorsStep.tsx              NEW
      ReviewStep.tsx                   NEW
    Mandate/
      MandatesPage.tsx                 NEW — list page
      MandateFormPage.tsx              NEW — create/edit form
      MandateSummaryPage.tsx           NEW — summary card
  components/
    Sidebar.tsx                        MODIFY — add Mandates nav item
  App.tsx                              MODIFY — add new routes
```

---

## 8. Error Handling

- File upload errors: inline under the file input (size exceeded, wrong type).
- API errors: toast notifications via a shared `useToast` hook (shadcn).
- Form validation: React Hook Form + Zod; errors displayed below each field.
- Confirm/create campaign failure: toast with retry option; stay on summary card.

---

## 9. Testing

- One test file per page: `onboarding.test.tsx`, `mandates.test.tsx`
- Cover: step navigation, Zod validation errors, confirm/reject flows, API mock responses
- Use existing `frontend/src/test/utils.tsx` test harness pattern
