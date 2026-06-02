# NTM RBAC + Route Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce 7-role RBAC on all backend API routes and restructure the frontend into role-segmented route modules with proper access guards.

**Architecture:** Backend gets a shared `require_role()` dependency factory applied to every router. Frontend gets a `RoleGuard` component wrapping each route group, plus Sidebar filtered by role. New CreativeStudio pages are created; all routes move from `/admin/*` flat tree to role-segmented paths (`/mandates`, `/campaigns`, `/creative-studio`, `/analytics`, `/kpi-dashboard`, `/admin`).

**Tech Stack:** FastAPI Depends, SQLAlchemy async, React Router v6 nested routes, Zustand, MSW mock handlers

---

## Role → Access Matrix

| Role | /mandates | /campaigns | /creative-studio | /analytics | /kpi-dashboard | /admin |
|---|---|---|---|---|---|---|
| platform_admin | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| tenant_admin | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| brand_manager | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| cmo | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| creative_lead | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ |
| campaign_manager | ✗ | ✓ | ✓ (view) | ✓ | ✓ | ✗ |
| viewer | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ |

## Role Home (unauthorized redirect target)

```
platform_admin   → /admin/tenants
tenant_admin     → /mandates
brand_manager    → /mandates
cmo              → /mandates
creative_lead    → /creative-studio
campaign_manager → /campaigns
viewer           → /analytics
```

---

## File Map

**Create:**
- `frontend/src/hooks/useRoleHome.ts`
- `frontend/src/components/RoleGuard.tsx`
- `frontend/src/pages/RoleHome/RoleHomePage.tsx`
- `frontend/src/pages/CreativeStudio/CreativeStudioPage.tsx`
- `frontend/src/pages/CreativeStudio/AssetDetailPage.tsx`
- `frontend/src/hooks/useCreatives.ts`
- `frontend/src/mocks/handlers/creatives.ts`

**Modify:**
- `backend/app/core/models.py` — add `UserRole` enum
- `backend/app/core/dependencies.py` — add `require_role()` factory
- `backend/app/routers/mandate.py` — apply `require_role`
- `backend/app/routers/campaign.py` — apply `require_role`
- `backend/app/routers/creatives.py` — apply `require_role`
- `backend/app/routers/creative_director.py` — apply `require_role`
- `backend/app/routers/digital_activator.py` — apply `require_role`
- `backend/app/routers/physical_activation.py` — apply `require_role`
- `backend/app/routers/analytics.py` — apply `require_role`
- `backend/app/routers/replanning.py` — apply `require_role`
- `backend/app/routers/report.py` — apply `require_role`
- `backend/app/routers/activations.py` — apply `require_role`
- `backend/app/routers/admin.py` — replace local `require_platform_admin` with shared
- `frontend/src/components/Sidebar.tsx` — filter nav by role
- `frontend/src/router.tsx` — full restructure with RoleGuard
- `frontend/src/mocks/handlers/auth.ts` — support all 7 roles
- `frontend/src/mocks/browser.ts` — register creatives handler

---

## Task 1: Backend — UserRole Enum

**Files:**
- Modify: `backend/app/core/models.py`

- [ ] **Step 1: Read the file**

```bash
cat backend/app/core/models.py
```

- [ ] **Step 2: Add UserRole enum after imports**

Find the `import uuid` line and add after it (before `Base = declarative_base()`):

```python
from enum import Enum

class UserRole(str, Enum):
    PLATFORM_ADMIN = "platform_admin"
    TENANT_ADMIN = "tenant_admin"
    BRAND_MANAGER = "brand_manager"
    CMO = "cmo"
    CREATIVE_LEAD = "creative_lead"
    CAMPAIGN_MANAGER = "campaign_manager"
    VIEWER = "viewer"
```

- [ ] **Step 3: Verify import works**

```bash
cd D:/staging/ntm && python -c "from backend.app.core.models import UserRole; print(list(UserRole))"
```

Expected output:
```
[<UserRole.PLATFORM_ADMIN: 'platform_admin'>, <UserRole.TENANT_ADMIN: 'tenant_admin'>, ...]
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/core/models.py
git commit -m "feat: add UserRole enum to core models"
```

---

## Task 2: Backend — require_role Dependency Factory

**Files:**
- Modify: `backend/app/core/dependencies.py`
- Test: `backend/app/core/tests/test_dependencies.py`

- [ ] **Step 1: Write the failing test**

Read `backend/app/core/tests/test_dependencies.py`, then add:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from backend.app.core.dependencies import require_role
from backend.app.core.models import UserRole


def make_user(role_name: str):
    user = MagicMock()
    user.role = MagicMock()
    user.role.name = role_name
    return user


@pytest.mark.asyncio
async def test_require_role_allows_matching_role():
    user = make_user("brand_manager")
    dep = require_role([UserRole.BRAND_MANAGER, UserRole.CMO])
    result = await dep(user=user)
    assert result is user


@pytest.mark.asyncio
async def test_require_role_blocks_non_matching_role():
    user = make_user("viewer")
    dep = require_role([UserRole.BRAND_MANAGER, UserRole.CMO])
    with pytest.raises(HTTPException) as exc_info:
        await dep(user=user)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_role_allows_platform_admin_when_listed():
    user = make_user("platform_admin")
    dep = require_role([UserRole.PLATFORM_ADMIN])
    result = await dep(user=user)
    assert result is user


@pytest.mark.asyncio
async def test_require_role_blocks_when_role_is_none():
    user = make_user("viewer")
    user.role = None
    dep = require_role([UserRole.BRAND_MANAGER])
    with pytest.raises(HTTPException) as exc_info:
        await dep(user=user)
    assert exc_info.value.status_code == 403
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd D:/staging/ntm && python -m pytest backend/app/core/tests/test_dependencies.py -k "require_role" -v
```

Expected: FAILED — `ImportError: cannot import name 'require_role'`

- [ ] **Step 3: Implement require_role in dependencies.py**

Read `backend/app/core/dependencies.py`, then add these imports at the top:

```python
from fastapi import HTTPException
from backend.app.core.models import UserRole
```

Add this function after `get_current_user_with_tenant`:

```python
def require_role(allowed_roles: list[UserRole]):
    """
    FastAPI dependency factory for role-based access control.

    Usage:
        @router.get("/resource")
        async def endpoint(user: User = Depends(require_role([UserRole.CMO, UserRole.BRAND_MANAGER]))):
            ...

    Raises HTTPException(403) if the authenticated user's role is not in allowed_roles.
    allowed_roles values are compared against user.role.name (the Role.name column).
    """
    allowed_names = {r.value for r in allowed_roles}

    async def _dependency(user: User = Depends(current_user)) -> User:
        if user.role is None or user.role.name not in allowed_names:
            raise HTTPException(
                status_code=403,
                detail=f"Access restricted. Allowed roles: {', '.join(sorted(allowed_names))}",
            )
        return user

    return _dependency
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd D:/staging/ntm && python -m pytest backend/app/core/tests/test_dependencies.py -k "require_role" -v
```

Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/dependencies.py backend/app/core/tests/test_dependencies.py
git commit -m "feat: add require_role dependency factory"
```

---

## Task 3: Backend — Apply RBAC to mandate.py

**Files:**
- Modify: `backend/app/routers/mandate.py`

- [ ] **Step 1: Read the file**

```bash
cat backend/app/routers/mandate.py
```

- [ ] **Step 2: Add imports at top of file**

After the existing imports, add:

```python
from backend.app.core.dependencies import require_role
from backend.app.core.models import UserRole

MANDATE_ROLES = [
    UserRole.BRAND_MANAGER,
    UserRole.CMO,
    UserRole.TENANT_ADMIN,
    UserRole.PLATFORM_ADMIN,
]
```

- [ ] **Step 3: Replace `user: User = Depends(current_user)` on every endpoint**

For every `@router.post`, `@router.get`, `@router.put` endpoint in `mandate.py`, change:

```python
user: User = Depends(current_user),
```

to:

```python
user: User = Depends(require_role(MANDATE_ROLES)),
```

Do this for ALL endpoints in the file (analyze_competitors, get_job_status, and any mandate CRUD endpoints).

- [ ] **Step 4: Verify no import errors**

```bash
cd D:/staging/ntm && python -c "from backend.app.routers.mandate import router; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/mandate.py
git commit -m "feat: apply RBAC to mandate router (brand_manager, cmo, tenant_admin, platform_admin)"
```

---

## Task 4: Backend — Apply RBAC to campaign.py

**Files:**
- Modify: `backend/app/routers/campaign.py`

- [ ] **Step 1: Read the file**

```bash
cat backend/app/routers/campaign.py
```

- [ ] **Step 2: Add imports + role constant**

```python
from backend.app.core.dependencies import require_role
from backend.app.core.models import UserRole

CAMPAIGN_ROLES = [
    UserRole.CAMPAIGN_MANAGER,
    UserRole.BRAND_MANAGER,
    UserRole.CMO,
    UserRole.TENANT_ADMIN,
    UserRole.PLATFORM_ADMIN,
]
```

- [ ] **Step 3: Replace current_user with require_role on all endpoints**

Change every:
```python
user: User = Depends(current_user),
```
to:
```python
user: User = Depends(require_role(CAMPAIGN_ROLES)),
```

- [ ] **Step 4: Verify**

```bash
cd D:/staging/ntm && python -c "from backend.app.routers.campaign import router; print('OK')"
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/campaign.py
git commit -m "feat: apply RBAC to campaign router"
```

---

## Task 5: Backend — Apply RBAC to remaining routers

**Files:**
- Modify: `backend/app/routers/creatives.py`
- Modify: `backend/app/routers/creative_director.py`
- Modify: `backend/app/routers/digital_activator.py`
- Modify: `backend/app/routers/physical_activation.py`
- Modify: `backend/app/routers/analytics.py`
- Modify: `backend/app/routers/replanning.py`
- Modify: `backend/app/routers/report.py`
- Modify: `backend/app/routers/activations.py`

Role assignments per router:

| Router | Roles |
|---|---|
| creatives.py | creative_lead, brand_manager, cmo, tenant_admin, platform_admin |
| creative_director.py | creative_lead, brand_manager, tenant_admin, platform_admin |
| digital_activator.py | campaign_manager, tenant_admin, platform_admin |
| physical_activation.py | campaign_manager, tenant_admin, platform_admin |
| analytics.py | all 7 roles (everyone can view analytics) |
| replanning.py | cmo, campaign_manager, tenant_admin, platform_admin |
| report.py | cmo, tenant_admin, platform_admin |
| activations.py | campaign_manager, brand_manager, cmo, tenant_admin, platform_admin |

- [ ] **Step 1: Read each file and apply the pattern from Task 3/4**

For each router file:

1. Add at top of file:
```python
from backend.app.core.dependencies import require_role
from backend.app.core.models import UserRole
```

2. Add the role constant (use the table above):
```python
# Example for creatives.py:
CREATIVE_ROLES = [
    UserRole.CREATIVE_LEAD,
    UserRole.BRAND_MANAGER,
    UserRole.CMO,
    UserRole.TENANT_ADMIN,
    UserRole.PLATFORM_ADMIN,
]
```

3. Replace every `user: User = Depends(current_user)` with `user: User = Depends(require_role(XXXXX_ROLES))`

For `analytics.py`, use ALL_ROLES:
```python
ALL_ROLES = [
    UserRole.PLATFORM_ADMIN, UserRole.TENANT_ADMIN, UserRole.BRAND_MANAGER,
    UserRole.CMO, UserRole.CREATIVE_LEAD, UserRole.CAMPAIGN_MANAGER, UserRole.VIEWER,
]
```

- [ ] **Step 2: Verify all routers import cleanly**

```bash
cd D:/staging/ntm && python -c "
from backend.app.routers.creatives import router as r1
from backend.app.routers.creative_director import router as r2
from backend.app.routers.digital_activator import router as r3
from backend.app.routers.physical_activation import router as r4
from backend.app.routers.analytics import router as r5
from backend.app.routers.replanning import router as r6
from backend.app.routers.report import router as r7
from backend.app.routers.activations import router as r8
print('All OK')
"
```

Expected: `All OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/creatives.py backend/app/routers/creative_director.py \
        backend/app/routers/digital_activator.py backend/app/routers/physical_activation.py \
        backend/app/routers/analytics.py backend/app/routers/replanning.py \
        backend/app/routers/report.py backend/app/routers/activations.py
git commit -m "feat: apply RBAC to all remaining routers"
```

---

## Task 6: Backend — Refactor admin.py to use shared require_role

**Files:**
- Modify: `backend/app/routers/admin.py`

- [ ] **Step 1: Read the file**

```bash
cat backend/app/routers/admin.py
```

- [ ] **Step 2: Add import**

```python
from backend.app.core.dependencies import require_role
from backend.app.core.models import UserRole
```

- [ ] **Step 3: Remove the local require_platform_admin function**

Delete this entire block from admin.py:
```python
async def require_platform_admin(user: User = Depends(current_user)) -> User:
    if user.role.name != "platform_admin":
        raise HTTPException(status_code=403, detail="Platform admin access required")
    return user
```

- [ ] **Step 4: Replace all uses of require_platform_admin**

In every endpoint, change:
```python
_: User = Depends(require_platform_admin),
```
to:
```python
_: User = Depends(require_role([UserRole.PLATFORM_ADMIN])),
```

- [ ] **Step 5: Verify**

```bash
cd D:/staging/ntm && python -c "from backend.app.routers.admin import router; print('OK')"
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/admin.py
git commit -m "refactor: admin router uses shared require_role dependency"
```

---

## Task 7: Frontend — useRoleHome Hook

**Files:**
- Create: `frontend/src/hooks/useRoleHome.ts`

- [ ] **Step 1: Create the file**

`frontend/src/hooks/useRoleHome.ts`:
```typescript
import { useAuthStore } from '@/store/useAuthStore'

/** Maps each role to its home route after login. */
export const ROLE_HOME: Record<string, string> = {
  platform_admin: '/admin/tenants',
  tenant_admin: '/mandates',
  brand_manager: '/mandates',
  cmo: '/mandates',
  creative_lead: '/creative-studio',
  campaign_manager: '/campaigns',
  viewer: '/analytics',
}

/**
 * Returns the home route for the currently authenticated user's role.
 * Falls back to '/mandates' for unknown roles.
 * Returns '/login' when not authenticated.
 */
export function useRoleHome(): string {
  const user = useAuthStore((s) => s.user)
  if (!user) return '/login'
  return ROLE_HOME[user.role] ?? '/mandates'
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd D:/staging/ntm/frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors related to `useRoleHome.ts`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/useRoleHome.ts
git commit -m "feat: add useRoleHome hook with role-to-path mapping"
```

---

## Task 8: Frontend — RoleGuard Component

**Files:**
- Create: `frontend/src/components/RoleGuard.tsx`
- Create: `frontend/src/pages/RoleHome/RoleHomePage.tsx`

- [ ] **Step 1: Create RoleGuard.tsx**

`frontend/src/components/RoleGuard.tsx`:
```typescript
import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/store/useAuthStore'
import { useRoleHome } from '@/hooks/useRoleHome'

interface RoleGuardProps {
  /** Role names allowed to access the wrapped routes. */
  allowedRoles: string[]
}

/**
 * Wraps a route group with role-based access control.
 *
 * - Not authenticated → redirect to /login
 * - Authenticated but wrong role → redirect to user's role home
 * - Correct role → render Outlet (children)
 */
export function RoleGuard({ allowedRoles }: RoleGuardProps) {
  const user = useAuthStore((s) => s.user)
  const roleHome = useRoleHome()

  if (!user) return <Navigate to="/login" replace />
  if (!allowedRoles.includes(user.role)) return <Navigate to={roleHome} replace />
  return <Outlet />
}
```

- [ ] **Step 2: Create RoleHomePage.tsx**

`frontend/src/pages/RoleHome/RoleHomePage.tsx`:
```typescript
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '@/store/useAuthStore'
import { useRoleHome } from '@/hooks/useRoleHome'

/**
 * Smart redirect at "/".
 * Unauthenticated → /login
 * Authenticated → role-specific home (e.g. /mandates, /campaigns)
 */
export function RoleHomePage() {
  const user = useAuthStore((s) => s.user)
  const roleHome = useRoleHome()

  if (!user) return <Navigate to="/login" replace />
  return <Navigate to={roleHome} replace />
}
```

- [ ] **Step 3: Verify TypeScript**

```bash
cd D:/staging/ntm/frontend && npx tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/RoleGuard.tsx frontend/src/pages/RoleHome/RoleHomePage.tsx
git commit -m "feat: add RoleGuard component and RoleHomePage smart redirect"
```

---

## Task 9: Frontend — Update Sidebar with Role Filtering

**Files:**
- Modify: `frontend/src/components/Sidebar.tsx`

- [ ] **Step 1: Read the file**

```bash
cat frontend/src/components/Sidebar.tsx
```

- [ ] **Step 2: Replace NAV_ITEMS with role-aware version**

Replace the entire `NAV_ITEMS` array with:

```typescript
import { Palette } from 'lucide-react'  // add to existing lucide import

interface NavItem {
  label: string
  to: string
  icon: React.ElementType
  allowedRoles: string[]
}

const ALL_ROLES = [
  'platform_admin', 'tenant_admin', 'brand_manager',
  'cmo', 'creative_lead', 'campaign_manager', 'viewer',
]

const NAV_ITEMS: NavItem[] = [
  {
    label: 'Mandates',
    to: '/mandates',
    icon: FileText,
    allowedRoles: ['brand_manager', 'cmo', 'tenant_admin', 'platform_admin'],
  },
  {
    label: 'Campaigns',
    to: '/campaigns',
    icon: Megaphone,
    allowedRoles: ['campaign_manager', 'brand_manager', 'cmo', 'tenant_admin', 'platform_admin'],
  },
  {
    label: 'Creative Studio',
    to: '/creative-studio',
    icon: Palette,
    allowedRoles: ['creative_lead', 'brand_manager', 'cmo', 'tenant_admin', 'platform_admin'],
  },
  {
    label: 'Analytics',
    to: '/analytics',
    icon: BarChart2,
    allowedRoles: ALL_ROLES,
  },
  {
    label: 'KPI Dashboard',
    to: '/kpi-dashboard',
    icon: Target,
    allowedRoles: ['cmo', 'campaign_manager', 'tenant_admin', 'platform_admin'],
  },
  {
    label: 'Tenants',
    to: '/admin/tenants',
    icon: Building2,
    allowedRoles: ['platform_admin'],
  },
  {
    label: 'Users',
    to: '/admin/users',
    icon: Users,
    allowedRoles: ['platform_admin'],
  },
  {
    label: 'Roles',
    to: '/admin/roles',
    icon: Shield,
    allowedRoles: ['platform_admin'],
  },
  {
    label: 'Audit Log',
    to: '/admin/audit',
    icon: ClipboardList,
    allowedRoles: ['platform_admin'],
  },
  {
    label: 'Health',
    to: '/admin/health',
    icon: Activity,
    allowedRoles: ['platform_admin'],
  },
]
```

- [ ] **Step 3: Filter items in the component body**

Inside the `Sidebar` function, before the return statement, add:

```typescript
const visibleItems = NAV_ITEMS.filter(item =>
  item.allowedRoles.includes(user?.role ?? '')
)
```

Then replace `{NAV_ITEMS.map(...)}` with `{visibleItems.map(...)}` in the JSX.

- [ ] **Step 4: Remove the hardcoded "Admin" role badge** (bottom section)

Replace the hardcoded badge:
```typescript
<span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium bg-red-100 text-red-800 border-red-200">
  Admin
</span>
```

with a dynamic badge using the user's actual role:
```typescript
<span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium bg-blue-100 text-blue-800 border-blue-200 capitalize">
  {user?.role?.replace('_', ' ') ?? 'Unknown'}
</span>
```

- [ ] **Step 5: Verify TypeScript**

```bash
cd D:/staging/ntm/frontend && npx tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/Sidebar.tsx
git commit -m "feat: sidebar filters nav items by user role"
```

---

## Task 10: Frontend — Restructure router.tsx

**Files:**
- Modify: `frontend/src/router.tsx`

- [ ] **Step 1: Read the full file**

```bash
cat frontend/src/router.tsx
```

- [ ] **Step 2: Rewrite router.tsx completely**

Replace the entire contents with:

```typescript
import { createBrowserRouter, Navigate } from 'react-router-dom'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { RoleGuard } from '@/components/RoleGuard'
import { AdminLayout } from '@/components/AdminLayout'
import { RoleHomePage } from '@/pages/RoleHome/RoleHomePage'

// Auth
import { LoginPage } from '@/pages/Login/LoginPage'

// Onboarding
import { OnboardingPage } from '@/pages/Onboarding/OnboardingPage'

// Mandate
import { MandatesPage } from '@/pages/Mandate/MandatesPage'
import { MandateFormPage } from '@/pages/Mandate/MandateFormPage'
import { MandateSummaryPage } from '@/pages/Mandate/MandateSummaryPage'

// Campaign
import { CampaignsPage } from '@/pages/Admin/Campaigns/CampaignsPage'
import { CampaignDetailPage } from '@/pages/Admin/Campaigns/CampaignDetailPage'
import { ConceptsPage } from '@/pages/Admin/Campaigns/ConceptsPage'
import { PlanPage } from '@/pages/Admin/Campaigns/PlanPage'
import { BudgetPage } from '@/pages/Admin/Campaigns/BudgetPage'
import { CreativesPage } from '@/pages/Admin/Campaigns/CreativesPage'
import { GoLivePage } from '@/pages/Admin/Campaigns/GoLivePage'
import { KpisPage } from '@/pages/Admin/Campaigns/KpisPage'
import { PhysicalLogPage } from '@/pages/Admin/Campaigns/PhysicalLogPage'
import { CIReportPage } from '@/pages/Admin/Campaigns/CIReportPage'

// Creative Studio
import { CreativeStudioPage } from '@/pages/CreativeStudio/CreativeStudioPage'
import { AssetDetailPage } from '@/pages/CreativeStudio/AssetDetailPage'

// Analytics
import { AnalyticsPage } from '@/pages/Admin/Analytics/AnalyticsPage'

// KPI Dashboard
import { KPIDashboardPage } from '@/pages/KPIDashboard/KPIDashboardPage'

// Admin
import { TenantsPage } from '@/pages/Admin/Tenants/TenantsPage'
import { UsersPage } from '@/pages/Admin/Users/UsersPage'
import { RolesPage } from '@/pages/Admin/Roles/RolesPage'
import { AuditLogPage } from '@/pages/Admin/AuditLog/AuditLogPage'
import { HealthPage } from '@/pages/Admin/Health/HealthPage'

const MANDATE_ROLES = ['brand_manager', 'cmo', 'tenant_admin', 'platform_admin']
const CAMPAIGN_ROLES = ['campaign_manager', 'brand_manager', 'cmo', 'tenant_admin', 'platform_admin']
const CREATIVE_ROLES = ['creative_lead', 'brand_manager', 'cmo', 'tenant_admin', 'platform_admin']
const KPI_ROLES = ['cmo', 'campaign_manager', 'tenant_admin', 'platform_admin']
const ADMIN_ROLES = ['platform_admin']
const ALL_ROLES = [
  'platform_admin', 'tenant_admin', 'brand_manager',
  'cmo', 'creative_lead', 'campaign_manager', 'viewer',
]

export const router = createBrowserRouter([
  // Smart home redirect — goes to role-specific page
  { path: '/', element: <RoleHomePage /> },

  // Public
  { path: '/login', element: <LoginPage /> },

  // Onboarding — any authenticated user
  {
    element: <ProtectedRoute />,
    children: [
      { path: '/onboarding', element: <OnboardingPage /> },
    ],
  },

  // Mandates — brand_manager, cmo, tenant_admin, platform_admin
  {
    path: '/mandates',
    element: <RoleGuard allowedRoles={MANDATE_ROLES} />,
    children: [
      {
        element: <AdminLayout />,
        children: [
          { index: true, element: <MandatesPage /> },
          { path: 'new', element: <MandateFormPage /> },
          { path: ':id/summary', element: <MandateSummaryPage /> },
        ],
      },
    ],
  },

  // Campaigns — campaign_manager, brand_manager, cmo, tenant_admin, platform_admin
  {
    path: '/campaigns',
    element: <RoleGuard allowedRoles={CAMPAIGN_ROLES} />,
    children: [
      {
        element: <AdminLayout />,
        children: [
          { index: true, element: <CampaignsPage /> },
          { path: ':id', element: <CampaignDetailPage /> },
          { path: ':id/concepts', element: <ConceptsPage /> },
          { path: ':id/plan', element: <PlanPage /> },
          { path: ':id/budget', element: <BudgetPage /> },
          { path: ':id/creatives', element: <CreativesPage /> },
          { path: ':id/go-live', element: <GoLivePage /> },
          { path: ':id/kpis', element: <KpisPage /> },
          { path: ':id/physical-log', element: <PhysicalLogPage /> },
          { path: ':id/ci-report', element: <CIReportPage /> },
        ],
      },
    ],
  },

  // Creative Studio — creative_lead, brand_manager, cmo, tenant_admin, platform_admin
  {
    path: '/creative-studio',
    element: <RoleGuard allowedRoles={CREATIVE_ROLES} />,
    children: [
      {
        element: <AdminLayout />,
        children: [
          { index: true, element: <CreativeStudioPage /> },
          { path: ':assetId', element: <AssetDetailPage /> },
        ],
      },
    ],
  },

  // Analytics — all authenticated roles
  {
    path: '/analytics',
    element: <RoleGuard allowedRoles={ALL_ROLES} />,
    children: [
      {
        element: <AdminLayout />,
        children: [
          { index: true, element: <AnalyticsPage /> },
          { path: ':mandateId', element: <AnalyticsPage /> },
        ],
      },
    ],
  },

  // KPI Dashboard — cmo, campaign_manager, tenant_admin, platform_admin
  {
    path: '/kpi-dashboard',
    element: <RoleGuard allowedRoles={KPI_ROLES} />,
    children: [
      {
        element: <AdminLayout />,
        children: [
          { index: true, element: <KPIDashboardPage /> },
        ],
      },
    ],
  },

  // Admin — platform_admin ONLY
  {
    path: '/admin',
    element: <RoleGuard allowedRoles={ADMIN_ROLES} />,
    children: [
      {
        element: <AdminLayout />,
        children: [
          { index: true, element: <Navigate to="/admin/tenants" replace /> },
          { path: 'tenants', element: <TenantsPage /> },
          { path: 'users', element: <UsersPage /> },
          { path: 'roles', element: <RolesPage /> },
          { path: 'audit', element: <AuditLogPage /> },
          { path: 'health', element: <HealthPage /> },
        ],
      },
    ],
  },

  // Catch-all — redirect to home
  { path: '*', element: <RoleHomePage /> },
])
```

- [ ] **Step 3: Verify TypeScript compiles (CreativeStudio imports will fail — expected until Task 11)**

```bash
cd D:/staging/ntm/frontend && npx tsc --noEmit 2>&1 | grep -v "CreativeStudio"
```

Expected: no errors except missing CreativeStudio files (resolved in Task 11)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/router.tsx
git commit -m "feat: restructure routes into role-segmented modules with RoleGuard"
```

---

## Task 11: Frontend — CreativeStudio Pages

**Files:**
- Create: `frontend/src/hooks/useCreatives.ts`
- Create: `frontend/src/pages/CreativeStudio/CreativeStudioPage.tsx`
- Create: `frontend/src/pages/CreativeStudio/AssetDetailPage.tsx`
- Create: `frontend/src/mocks/handlers/creatives.ts`

- [ ] **Step 1: Create useCreatives hook**

`frontend/src/hooks/useCreatives.ts`:
```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'

export interface Creative {
  id: string
  campaign_id: string
  asset_type: 'image' | 'audio' | 'video' | 'copy' | 'script'
  asset_url: string | null
  status: 'ai_draft' | 'internal_review' | 'client_review' | 'approved' | 'revision_requested' | 'rejected'
  message_variant: string
  format_spec: string
  notes: string | null
  created_at: string
}

export function useCreatives(campaignId?: string) {
  return useQuery<Creative[]>({
    queryKey: ['creatives', campaignId],
    queryFn: async () => {
      const url = campaignId
        ? `/creatives?campaign_id=${campaignId}`
        : '/creatives'
      const { data } = await apiClient.get(url)
      return data
    },
    enabled: true,
  })
}

export function useCreative(assetId: string) {
  return useQuery<Creative>({
    queryKey: ['creative', assetId],
    queryFn: async () => {
      const { data } = await apiClient.get(`/creatives/${assetId}`)
      return data
    },
    enabled: !!assetId,
  })
}

export function useUpdateCreativeStatus() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({
      id,
      status,
      notes,
    }: {
      id: string
      status: Creative['status']
      notes?: string
    }) => {
      const { data } = await apiClient.patch(`/creatives/${id}/status`, { status, notes })
      return data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['creatives'] })
      qc.invalidateQueries({ queryKey: ['creative'] })
    },
  })
}
```

- [ ] **Step 2: Create MSW mock handler for creatives**

`frontend/src/mocks/handlers/creatives.ts`:
```typescript
import { http, HttpResponse } from 'msw'

const MOCK_CREATIVES = [
  {
    id: 'asset-001',
    campaign_id: 'campaign-001',
    asset_type: 'image',
    asset_url: 'https://placehold.co/800x600?text=Hero+Banner',
    status: 'client_review',
    message_variant: 'Variant A',
    format_spec: '1200x628px',
    notes: null,
    created_at: new Date().toISOString(),
  },
  {
    id: 'asset-002',
    campaign_id: 'campaign-001',
    asset_type: 'copy',
    asset_url: null,
    status: 'ai_draft',
    message_variant: 'Variant B',
    format_spec: 'Social caption',
    notes: 'Tone: energetic, max 280 chars',
    created_at: new Date().toISOString(),
  },
  {
    id: 'asset-003',
    campaign_id: 'campaign-001',
    asset_type: 'audio',
    asset_url: null,
    status: 'approved',
    message_variant: 'Radio VO',
    format_spec: '30s MP3',
    notes: null,
    created_at: new Date().toISOString(),
  },
]

export const creativesHandlers = [
  http.get('/api/v1/creatives', () => {
    return HttpResponse.json(MOCK_CREATIVES)
  }),

  http.get('/api/v1/creatives/:id', ({ params }) => {
    const creative = MOCK_CREATIVES.find((c) => c.id === params.id)
    if (!creative) return HttpResponse.json({ detail: 'Not found' }, { status: 404 })
    return HttpResponse.json(creative)
  }),

  http.patch('/api/v1/creatives/:id/status', async ({ params, request }) => {
    const body = await request.json() as { status: string; notes?: string }
    const creative = MOCK_CREATIVES.find((c) => c.id === params.id)
    if (!creative) return HttpResponse.json({ detail: 'Not found' }, { status: 404 })
    creative.status = body.status as typeof creative.status
    if (body.notes) creative.notes = body.notes
    return HttpResponse.json(creative)
  }),
]
```

- [ ] **Step 3: Create CreativeStudioPage.tsx**

`frontend/src/pages/CreativeStudio/CreativeStudioPage.tsx`:
```typescript
import { Link } from 'react-router-dom'
import { PageHeader } from '@/components/PageHeader'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useCreatives, type Creative } from '@/hooks/useCreatives'
import { Image, Music, Video, FileText, AlignLeft } from 'lucide-react'

const STATUS_BADGE: Record<Creative['status'], { label: string; className: string }> = {
  ai_draft:          { label: 'AI Draft',          className: 'bg-gray-100 text-gray-700 border-gray-200' },
  internal_review:   { label: 'Internal Review',   className: 'bg-yellow-100 text-yellow-700 border-yellow-200' },
  client_review:     { label: 'Client Review',     className: 'bg-blue-100 text-blue-700 border-blue-200' },
  approved:          { label: 'Approved',           className: 'bg-green-100 text-green-700 border-green-200' },
  revision_requested:{ label: 'Revision Requested', className: 'bg-orange-100 text-orange-700 border-orange-200' },
  rejected:          { label: 'Rejected',           className: 'bg-red-100 text-red-700 border-red-200' },
}

const ASSET_ICON: Record<Creative['asset_type'], React.ElementType> = {
  image:  Image,
  audio:  Music,
  video:  Video,
  copy:   AlignLeft,
  script: FileText,
}

export function CreativeStudioPage() {
  const { data: creatives, isLoading, error } = useCreatives()

  if (isLoading) return <div className="p-8 text-muted-foreground">Loading assets…</div>
  if (error)    return <div className="p-8 text-destructive">Failed to load assets.</div>

  return (
    <div className="p-6 space-y-6">
      <PageHeader title="Creative Studio" subtitle="Review and approve all campaign creative assets" />

      {(!creatives || creatives.length === 0) && (
        <p className="text-muted-foreground">No creative assets yet. Assets appear here once agents generate them.</p>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {creatives?.map((asset) => {
          const badge = STATUS_BADGE[asset.status]
          const Icon = ASSET_ICON[asset.asset_type]
          return (
            <Link key={asset.id} to={`/creative-studio/${asset.id}`}>
              <Card className="hover:shadow-md transition-shadow cursor-pointer">
                <CardHeader className="flex flex-row items-center gap-3 pb-2">
                  <div className="rounded-md bg-muted p-2">
                    <Icon className="h-5 w-5 text-muted-foreground" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <CardTitle className="text-sm font-medium truncate">
                      {asset.message_variant}
                    </CardTitle>
                    <p className="text-xs text-muted-foreground capitalize">
                      {asset.asset_type} · {asset.format_spec}
                    </p>
                  </div>
                </CardHeader>
                <CardContent>
                  {asset.asset_url && asset.asset_type === 'image' && (
                    <img
                      src={asset.asset_url}
                      alt={asset.message_variant}
                      className="w-full h-32 object-cover rounded mb-3"
                    />
                  )}
                  <Badge className={badge.className}>{badge.label}</Badge>
                </CardContent>
              </Card>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Create AssetDetailPage.tsx**

`frontend/src/pages/CreativeStudio/AssetDetailPage.tsx`:
```typescript
import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { PageHeader } from '@/components/PageHeader'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { useCreative, useUpdateCreativeStatus, type Creative } from '@/hooks/useCreatives'
import { useAuthStore } from '@/store/useAuthStore'

const STATUS_BADGE: Record<Creative['status'], { label: string; className: string }> = {
  ai_draft:          { label: 'AI Draft',          className: 'bg-gray-100 text-gray-700' },
  internal_review:   { label: 'Internal Review',   className: 'bg-yellow-100 text-yellow-700' },
  client_review:     { label: 'Client Review',     className: 'bg-blue-100 text-blue-700' },
  approved:          { label: 'Approved',           className: 'bg-green-100 text-green-700' },
  revision_requested:{ label: 'Revision Requested', className: 'bg-orange-100 text-orange-700' },
  rejected:          { label: 'Rejected',           className: 'bg-red-100 text-red-700' },
}

/** Roles that can approve/reject assets */
const APPROVAL_ROLES = ['creative_lead', 'brand_manager', 'cmo', 'tenant_admin', 'platform_admin']

export function AssetDetailPage() {
  const { assetId } = useParams<{ assetId: string }>()
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const [revisionNote, setRevisionNote] = useState('')

  const { data: asset, isLoading } = useCreative(assetId!)
  const { mutate: updateStatus, isPending } = useUpdateCreativeStatus()

  const canApprove = user ? APPROVAL_ROLES.includes(user.role) : false

  const handleApprove = () => {
    updateStatus({ id: assetId!, status: 'approved' }, { onSuccess: () => navigate('/creative-studio') })
  }

  const handleRequestRevision = () => {
    if (!revisionNote.trim()) return
    updateStatus(
      { id: assetId!, status: 'revision_requested', notes: revisionNote },
      { onSuccess: () => navigate('/creative-studio') }
    )
  }

  const handleReject = () => {
    updateStatus({ id: assetId!, status: 'rejected' }, { onSuccess: () => navigate('/creative-studio') })
  }

  if (isLoading) return <div className="p-8 text-muted-foreground">Loading asset…</div>
  if (!asset)   return <div className="p-8 text-destructive">Asset not found.</div>

  const badge = STATUS_BADGE[asset.status]

  return (
    <div className="p-6 space-y-6 max-w-3xl mx-auto">
      <PageHeader
        title={asset.message_variant}
        subtitle={`${asset.asset_type} · ${asset.format_spec}`}
      />

      <Badge className={badge.className}>{badge.label}</Badge>

      {/* Asset Preview */}
      <Card>
        <CardContent className="pt-6">
          {asset.asset_type === 'image' && asset.asset_url && (
            <img src={asset.asset_url} alt={asset.message_variant} className="w-full rounded" />
          )}
          {asset.asset_type === 'audio' && asset.asset_url && (
            <audio controls src={asset.asset_url} className="w-full" />
          )}
          {asset.asset_type === 'video' && asset.asset_url && (
            <video controls src={asset.asset_url} className="w-full rounded" />
          )}
          {(asset.asset_type === 'copy' || asset.asset_type === 'script') && (
            <pre className="whitespace-pre-wrap text-sm font-mono bg-muted p-4 rounded">
              {asset.notes ?? 'No content generated yet.'}
            </pre>
          )}
          {!asset.asset_url && asset.asset_type !== 'copy' && asset.asset_type !== 'script' && (
            <p className="text-muted-foreground text-sm">Asset not yet generated.</p>
          )}
        </CardContent>
      </Card>

      {/* Approval Actions — only for allowed roles */}
      {canApprove && (
        <div className="space-y-4">
          <div className="flex gap-3">
            <Button onClick={handleApprove} disabled={isPending} className="bg-green-600 hover:bg-green-700">
              Approve
            </Button>
            <Button onClick={handleReject} disabled={isPending} variant="destructive">
              Reject
            </Button>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Request Revision</label>
            <textarea
              value={revisionNote}
              onChange={(e) => setRevisionNote(e.target.value)}
              placeholder="Describe the revision needed…"
              className="w-full min-h-[80px] rounded border border-input bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-ring"
            />
            <Button
              variant="outline"
              onClick={handleRequestRevision}
              disabled={isPending || !revisionNote.trim()}
            >
              Request Revision
            </Button>
          </div>
        </div>
      )}

      <Button variant="ghost" onClick={() => navigate('/creative-studio')}>
        ← Back to Studio
      </Button>
    </div>
  )
}
```

- [ ] **Step 5: Register creatives handler in browser.ts**

Read `frontend/src/mocks/browser.ts`, then add `creativesHandlers` to the handlers array:

```typescript
import { creativesHandlers } from './handlers/creatives'

// In the setupWorker call, add creativesHandlers to the spread:
export const worker = setupWorker(
  ...authHandlers,
  ...tenantsHandlers,
  ...usersHandlers,
  ...rolesHandlers,
  ...auditHandlers,
  ...healthHandlers,
  ...analyticsHandlers,
  ...campaignsHandlers,
  ...mandatesHandlers,
  ...creativesHandlers,  // ← add this
)
```

- [ ] **Step 6: Verify TypeScript compiles cleanly**

```bash
cd D:/staging/ntm/frontend && npx tsc --noEmit 2>&1 | head -30
```

Expected: 0 errors

- [ ] **Step 7: Commit**

```bash
git add frontend/src/hooks/useCreatives.ts \
        frontend/src/pages/CreativeStudio/ \
        frontend/src/mocks/handlers/creatives.ts \
        frontend/src/mocks/browser.ts
git commit -m "feat: add CreativeStudio pages (gallery + asset detail) and useCreatives hook"
```

---

## Task 12: Frontend — Update Mock Auth to Support All 7 Roles

**Files:**
- Modify: `frontend/src/mocks/handlers/auth.ts`

This enables testing each role's experience without a real backend.

- [ ] **Step 1: Read the file**

```bash
cat frontend/src/mocks/handlers/auth.ts
```

- [ ] **Step 2: Update login handler to derive role from email prefix**

Replace the login handler with a version that maps email prefixes to roles:

```typescript
// Role mapping: email prefix determines role in mock environment
// e.g. admin@x.com → platform_admin, cmo@x.com → cmo
const EMAIL_ROLE_MAP: Record<string, string> = {
  admin:            'platform_admin',
  platform:         'platform_admin',
  tenant:           'tenant_admin',
  brand:            'brand_manager',
  cmo:              'cmo',
  creative:         'creative_lead',
  campaign:         'campaign_manager',
  viewer:           'viewer',
}

function getRoleFromEmail(email: string): string {
  const prefix = email.split('@')[0].split('.')[0].toLowerCase()
  return EMAIL_ROLE_MAP[prefix] ?? 'brand_manager'
}

// In authHandlers, replace the login handler body:
http.post('/api/v1/auth/login', async ({ request }) => {
  const body = await request.json() as { email: string; password: string }
  const role = getRoleFromEmail(body.email)
  return HttpResponse.json({
    token: 'mock-jwt-token',
    user: {
      id: `user-${body.email}`,
      email: body.email,
      role,
    },
  })
}),

// Also update register handler:
http.post('/api/v1/auth/register', async ({ request }) => {
  const body = await request.json() as { email: string; password: string }
  const email = body.email.toLowerCase().trim()

  if (isRegistered(email)) {
    return HttpResponse.json({ detail: 'User already exists' }, { status: 409 })
  }

  saveRegistered(email)
  const role = getRoleFromEmail(email)

  return HttpResponse.json({
    token: 'mock-jwt-token',
    user: {
      id: `user-${email}`,
      email: body.email,
      role,
    },
  })
}),
```

- [ ] **Step 3: Verify TypeScript**

```bash
cd D:/staging/ntm/frontend && npx tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/mocks/handlers/auth.ts
git commit -m "feat: mock auth derives role from email prefix for RBAC testing"
```

---

## Task 13: Verification

- [ ] **Step 1: Run backend tests**

```bash
cd D:/staging/ntm && python -m pytest backend/ -x -q 2>&1 | tail -20
```

Expected: all tests pass (no import errors from role changes)

- [ ] **Step 2: Build frontend**

```bash
cd D:/staging/ntm/frontend && npm run build 2>&1 | tail -20
```

Expected: `built in X.XXs` with no TypeScript errors

- [ ] **Step 3: Verify role routing manually (dev server)**

```bash
cd D:/staging/ntm/frontend && npm run dev
```

Test matrix:
- Login as `cmo@test.com` → lands on `/mandates` ✓
- Login as `creative@test.com` → lands on `/creative-studio` ✓
- Login as `campaign@test.com` → lands on `/campaigns` ✓
- Login as `admin@test.com` → lands on `/admin/tenants` ✓
- Login as `viewer@test.com` → lands on `/analytics` ✓
- As `viewer`, navigate to `/mandates` → redirected back to `/analytics` ✓
- As `creative_lead`, navigate to `/admin/tenants` → redirected to `/creative-studio` ✓

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore: final verification — RBAC + route restructure complete"
```

---

## Self-Review

**Spec coverage check:**
- ✅ All 7 roles defined (`UserRole` enum, Task 1)
- ✅ `require_role()` factory with tests (Task 2)
- ✅ Applied to: mandate, campaign, creatives, creative_director, digital_activator, physical_activation, analytics, replanning, report, activations, admin (Tasks 3–6)
- ✅ Frontend `RoleGuard` redirects unauthorized users to role home (Task 8)
- ✅ Sidebar filters nav items by role (Task 9)
- ✅ Router restructured: /mandates, /campaigns, /creative-studio, /analytics, /kpi-dashboard, /admin (Task 10)
- ✅ New CreativeStudio pages: gallery + asset detail with approve/reject (Task 11)
- ✅ Mock auth supports all 7 roles via email prefix (Task 12)
- ✅ Smart `/` redirect to role home (Task 8 — RoleHomePage)

**Placeholder scan:** None found.

**Type consistency:**
- `Creative['status']` used in `useCreatives`, `CreativeStudioPage`, `AssetDetailPage` — consistent.
- `UserRole` enum values match string names in `require_role` comparison — consistent.
- `user.role` in frontend always `string`, matched against `string[]` in `RoleGuard.allowedRoles` — consistent.
