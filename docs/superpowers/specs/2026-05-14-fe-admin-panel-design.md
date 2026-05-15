# Frontend Admin Panel Design Spec (TASK-028)

**Goal:** Build the NTM platform_admin panel — a Vite + React 18 SPA with login, left-sidebar layout, and five admin sections (Tenants, Users, Roles, Audit Log, Health) backed by MSW mocks.

**Architecture:** Domain-module pattern. React Query owns all server state. Zustand owns auth state. shadcn/ui provides all component primitives. MSW browser-mode provides mock API responses in dev. Each feature is a self-contained module (page + hook + MSW handler).

**Tech Stack:** React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui, Zustand (+ persist middleware), React Query v5, react-router-dom v6, axios, MSW v2, Recharts, zod, react-hook-form

---

## 1. Project Bootstrap

Scaffold `frontend/` using `npm create vite@latest . -- --template react-ts` then install:

```
npm install @tanstack/react-query zustand react-router-dom axios msw recharts zod react-hook-form @hookform/resolvers
npx shadcn@latest init
npx shadcn@latest add button input label dialog table select badge card form
```

Tailwind config: `content: ["./index.html", "./src/**/*.{ts,tsx}"]`.

MSW init: `npx msw init public/ --save`.

---

## 2. Folder Structure

```
frontend/src/
  api/
    client.ts           ← axios instance with JWT interceptor + 401 handler
    admin.ts            ← all admin API functions (getTenants, createTenant, etc.)
  components/
    AdminLayout.tsx     ← left sidebar (240px) + <Outlet /> main area
    Sidebar.tsx         ← nav links, user info, logout button
    PageHeader.tsx      ← shared title + description header
    ProtectedRoute.tsx  ← role guard: platform_admin only
  hooks/
    useTenants.ts       ← useQuery + useMutation for tenants
    useUsers.ts         ← useQuery + useMutation for users
    useRoles.ts         ← useQuery for roles (read-only)
    useAudit.ts         ← useQuery with filter params
    useHealth.ts        ← useQuery with refetchInterval: 30000
  mocks/
    browser.ts          ← MSW setupWorker(…handlers)
    handlers/
      auth.ts           ← POST /api/v1/auth/login
      tenants.ts        ← GET/POST/PATCH /api/v1/admin/tenants
      users.ts          ← GET/POST/PATCH /api/v1/admin/tenants/:id/users, /users/:id
      audit.ts          ← GET /api/v1/admin/audit (with query param filtering)
      health.ts         ← GET /api/v1/admin/health
  pages/
    Login/
      LoginPage.tsx
    Admin/
      Tenants/
        TenantsPage.tsx
      Users/
        UsersPage.tsx
      Roles/
        RolesPage.tsx
      AuditLog/
        AuditLogPage.tsx
      Health/
        HealthPage.tsx
  store/
    useAuthStore.ts     ← { token, user, login(), logout() } persisted to localStorage
  types/
    admin.ts            ← Tenant, User, Role, AuditEntry, HealthStatus TypeScript types
  App.tsx               ← route tree
  main.tsx              ← MSW start in DEV, QueryClientProvider, RouterProvider
```

---

## 3. Auth Layer

### LoginPage
- Centered card (shadcn/ui `Card`), email + password inputs
- `react-hook-form` + `zod` schema: `{ email: z.string().email(), password: z.string().min(1) }`
- On submit: `POST /api/v1/auth/login` → `{ token: string, user: { id, email, role } }`
- On success: `useAuthStore().login(token, user)` → navigate to `/admin/tenants`
- On error: inline error message below form

### Zustand Auth Store (`store/useAuthStore.ts`)
```ts
interface AuthState {
  token: string | null
  user: { id: string; email: string; role: string } | null
  login(token: string, user: AuthState['user']): void
  logout(): void
}
```
Persisted to `localStorage` key `ntm-auth` via `zustand/middleware` `persist`.

### Axios Client (`api/client.ts`)
- Single `axios.create({ baseURL: '/api/v1' })` instance
- Request interceptor: attaches `Authorization: Bearer <token>` from store
- Response interceptor: on 401 → calls `logout()` + `window.location.replace('/login')`

### ProtectedRoute (`components/ProtectedRoute.tsx`)
- Reads `useAuthStore().user`
- No user → `<Navigate to="/login" />`
- User role !== `"platform_admin"` → `<Navigate to="/403" />`
- Otherwise → `<Outlet />`

---

## 4. Routing (`App.tsx`)

```
/                         → redirect to /admin/tenants
/login                    → LoginPage
/admin                    → ProtectedRoute → AdminLayout
  /admin/tenants          → TenantsPage   (index)
  /admin/users            → UsersPage
  /admin/roles            → RolesPage
  /admin/audit            → AuditLogPage
  /admin/health           → HealthPage
/403                      → simple "Access Denied" page
```

---

## 5. Admin Layout

**AdminLayout** (`components/AdminLayout.tsx`):
```tsx
<div className="flex h-screen bg-background">
  <Sidebar />
  <main className="flex-1 overflow-y-auto p-6">
    <Outlet />
  </main>
</div>
```

**Sidebar** (`components/Sidebar.tsx`):
- Fixed width 240px, `border-r bg-card`
- Top: "NTM Admin" title + logo mark
- Nav items using `NavLink` (react-router) with active state via `isActive` → `bg-accent text-accent-foreground`
- Nav items: Tenants (`/admin/tenants`), Users (`/admin/users`), Roles (`/admin/roles`), Audit Log (`/admin/audit`), Health (`/admin/health`)
- Bottom: user email + role badge + Logout button (calls `logout()` → navigate to `/login`)

**PageHeader** (`components/PageHeader.tsx`):
```tsx
<div className="mb-6">
  <h1 className="text-2xl font-semibold">{title}</h1>
  <p className="text-muted-foreground text-sm">{description}</p>
</div>
```

---

## 6. Feature Pages

### Tenants (`pages/Admin/Tenants/TenantsPage.tsx`)
- `useTenants()` → shadcn/ui `DataTable` with columns: Name, Status (Badge: active/inactive), Created, Actions
- "New Tenant" button → `Dialog` with form: name (required)
- On submit: `useCreateTenant()` mutation → invalidates `['tenants']` query key
- Row action menu (shadcn/ui `DropdownMenu`): Activate / Deactivate → `useToggleTenant()` mutation

### Users (`pages/Admin/Users/UsersPage.tsx`)
- Tenant selector (`Select`) at top — populated by `useTenants()`; selection stored in local `useState`
- `useUsers(tenantId)` → `DataTable`: Email, Role (Badge), Status, Created, Actions
- "New User" button → `Dialog` form: email, password, role dropdown (7 options from `ROLES` constant)
- On submit: `useCreateUser(tenantId)` → invalidates `['users', tenantId]`
- Row action: Deactivate → `useDeactivateUser()` mutation

**ROLES constant** (in `types/admin.ts`):
```ts
export const ROLES = [
  'platform_admin', 'tenant_admin', 'brand_manager',
  'cmo', 'creative_lead', 'campaign_manager', 'viewer'
] as const
```

### Roles (`pages/Admin/Roles/RolesPage.tsx`)
- `useRoles()` → read-only `DataTable`: Role Name, Permissions (badge chips), User Count
- No mutations — roles are fixed in backend config
- Uses `useQuery` with `staleTime: Infinity` (never refetch)

### Audit Log (`pages/Admin/AuditLog/AuditLogPage.tsx`)
- Filter bar: Entity Type `Select`, Actor email `Input`, Date range (two `Input type="date"`)
- "Apply" button triggers React Query refetch with filter state as query key: `['audit', filters]`
- `DataTable`: Timestamp, Actor, Action, Entity Type, Entity ID, Detail — paginated (page size 20)
- `useAudit(filters)` hook passes filters as query params to `GET /api/v1/admin/audit`

### Health (`pages/Admin/Health/HealthPage.tsx`)
- `useHealth()` — `refetchInterval: 30_000`
- Three `Card` components: API, PostgreSQL, Celery Worker
  - Each card: service name, status badge (green=ok, yellow=degraded, red=down), last-checked timestamp
- One Recharts `LineChart` (200px height) showing API latency (ms) for the last 10 polls
  - Latency history stored in a `useRef` array, appended on each successful health response

---

## 7. MSW Handlers

All handlers defined in `mocks/handlers/`. In-memory stores (arrays) simulate a real database within the browser session — mutations (create, toggle) update the in-memory store and subsequent GETs reflect the change.

**Seed data:**
- Tenants: Acme Corp (active), BrandCo (active), MediaGroup (inactive)
- Users: 5 users across the 3 tenants, mixed roles
- Audit entries: 20 entries with varied entity types and actors
- Health: `{ api: 'ok', db: 'ok', celery: 'ok', latency_ms: 42 }`
- Auth: any email/password → returns `{ token: 'mock-jwt', user: { id: '1', email, role: 'platform_admin' } }`

---

## 8. Types (`types/admin.ts`)

```ts
export interface Tenant {
  id: string; name: string; is_active: boolean; created_at: string
}
export interface User {
  id: string; email: string; role: string; is_active: boolean
  tenant_id: string; created_at: string
}
export interface Role {
  id: string; name: string; permissions: string[]; user_count: number
}
export interface AuditEntry {
  id: string; timestamp: string; actor: string; action: string
  entity_type: string; entity_id: string; detail: string
}
export interface HealthStatus {
  api: 'ok' | 'degraded' | 'down'
  db: 'ok' | 'degraded' | 'down'
  celery: 'ok' | 'degraded' | 'down'
  latency_ms: number
}
```

---

## 9. Out of Scope

- Backend admin API endpoints (separate task)
- Role editing / permission changes (roles are fixed)
- Multi-tenant user access (junction table) management
- Password reset flow
- Pagination controls for Users / Tenants (MSW data set is small)
