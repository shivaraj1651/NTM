# Dynamic Login — Multi-Tenant RBAC Self-Registration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make login/register open to any tenant — derive role from email prefix, auto-create tenant from email domain, show live preview in UI.

**Architecture:** Email `roleprefix@tenantdomain.tld` is parsed on both backend (register endpoint auto-UPSERTs tenant + assigns role) and frontend (live badge preview). MSW mock handler gains `tenant_id` in responses. No new endpoints, no new DB columns.

**Tech Stack:** FastAPI + SQLAlchemy async, React 18 + react-hook-form + Zod, MSW v2, Vitest, pytest-asyncio

---

## File Map

| File | Change |
|------|--------|
| `backend/app/routers/auth_session.py` | Parse email → derive role + tenant, UPSERT tenant, assign role in `/register` |
| `backend/tests/routers/test_auth_session.py` | Add register tests for new tenant auto-create + role derivation |
| `frontend/src/mocks/handlers/auth.ts` | Add `tenant_id` to login + register mock user payload |
| `frontend/src/pages/Login/LoginPage.tsx` | Live role/tenant preview badge in register form |
| `frontend/src/test/login.test.tsx` | Add test for role preview badge visibility |

---

## Task 1: Backend — parse email + UPSERT tenant in `/register`

**Files:**
- Modify: `backend/app/routers/auth_session.py`

**Context:** `Tenant` model has `id` (uuid str), `name` (str, used as slug), `is_active` (bool), `created_at`. No `slug` column — use `name` as the slug. `Role` model has `name` (unique). `UserRole` enum defines valid role names. Register endpoint currently hard-codes `tenant_id = "tenant-acme"` and defaults role to `brand_manager` from request body.

- [ ] **Step 1: Add email parsing helper at top of `auth_session.py`**

Replace the import block and add the helper after the `router` definition. Open `backend/app/routers/auth_session.py` and add this helper function after the `router = APIRouter(...)` line:

```python
import uuid as _uuid
from datetime import UTC, datetime

from backend.app.core.models import Tenant  # add Tenant to existing import

_EMAIL_ROLE_MAP: dict[str, str] = {
    "admin":    "platform_admin",
    "platform": "platform_admin",
    "tenant":   "tenant_admin",
    "brand":    "brand_manager",
    "cmo":      "cmo",
    "creative": "creative_lead",
    "campaign": "campaign_manager",
    "viewer":   "viewer",
}


def _parse_email(email: str) -> tuple[str, str]:
    """Return (role_name, tenant_slug) derived from email."""
    local, domain = email.lower().split("@", 1)
    prefix = local.split(".")[0]
    tenant_slug = domain.split(".")[0]
    role_name = _EMAIL_ROLE_MAP.get(prefix, "brand_manager")
    return role_name, tenant_slug
```

- [ ] **Step 2: Rewrite the `/register` endpoint**

Replace the entire `register` function in `backend/app/routers/auth_session.py`:

```python
@router.post("/register", status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)) -> dict:
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail={"error_code": "USER_EXISTS", "message": "User already exists"})

    role_name, tenant_slug = _parse_email(body.email)

    # UPSERT tenant by name/slug
    tenant_row = (await db.execute(select(Tenant).where(Tenant.name == tenant_slug))).scalar_one_or_none()
    if tenant_row is None:
        tenant_row = Tenant(
            id=str(_uuid.uuid4()),
            name=tenant_slug,
            is_active=True,
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db.add(tenant_row)
        await db.flush()  # get tenant_row.id without full commit

    role_row = (await db.execute(select(Role).where(Role.name == role_name))).scalar_one_or_none()
    if role_row is None:
        raise HTTPException(status_code=400, detail={"error_code": "BAD_ROLE", "message": f"Unknown role: {role_name}"})

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        tenant_id=tenant_row.id,
        role_id=role_row.id,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    user.role = role_row
    user.tenant_id = tenant_row.id
    token = await write_jwt(user)
    return _user_payload(user, token)
```

- [ ] **Step 3: Verify the imports at the top of `auth_session.py` are complete**

The top of the file should have these imports (add any missing):

```python
"""JSON session auth: POST /api/v1/auth/login and /register (frontend contract)."""
import uuid as _uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.auth import write_jwt
from backend.app.core.auth_helpers import hash_password, verify_password
from backend.app.core.models import Role, Tenant, User
from backend.app.db import get_db
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/auth_session.py
git commit -m "feat(auth): auto-derive role+tenant from email on register"
```

---

## Task 2: Backend tests — register with auto-tenant + role derivation

**Files:**
- Modify: `backend/tests/routers/test_auth_session.py`

**Context:** Existing test uses `_FakeSession` that always returns `None`. Need a more capable fake for register: it must handle multiple `execute` calls (duplicate check → None, tenant lookup → None or existing, role lookup → Role row, then adds/flushes/commits). Use `pytest-asyncio` with `@pytest.mark.asyncio`.

- [ ] **Step 1: Add Role + Tenant + User fakes and new register tests**

Append to `backend/tests/routers/test_auth_session.py`:

```python
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.core.models import Role, Tenant, User


def _make_role(name: str) -> Role:
    r = Role.__new__(Role)
    r.id = str(uuid.uuid4())
    r.name = name
    r.permissions = []
    return r


def _make_tenant(name: str) -> Tenant:
    t = Tenant.__new__(Tenant)
    t.id = str(uuid.uuid4())
    t.name = name
    t.is_active = True
    return t


class _RegSession:
    """Fake AsyncSession for register endpoint tests."""

    def __init__(self, *, tenant_exists: bool = False, role_name: str = "brand_manager"):
        self._tenant_exists = tenant_exists
        self._role_name = role_name
        self._call = 0
        self._added = []
        self.tenant = _make_tenant("acme") if tenant_exists else None
        self.role = _make_role(role_name)

    async def execute(self, *args, **kwargs):
        self._call += 1
        result = MagicMock()
        if self._call == 1:
            # duplicate-user check → no existing user
            result.scalar_one_or_none.return_value = None
        elif self._call == 2:
            # tenant lookup
            result.scalar_one_or_none.return_value = self.tenant
        elif self._call == 3:
            # role lookup
            result.scalar_one_or_none.return_value = self.role
        else:
            result.scalar_one_or_none.return_value = None
        return result

    def add(self, obj):
        self._added.append(obj)

    async def flush(self):
        # assign id to any new Tenant that was added
        for obj in self._added:
            if isinstance(obj, Tenant) and not hasattr(obj, 'id'):
                obj.id = str(uuid.uuid4())

    async def commit(self):
        pass

    async def refresh(self, obj):
        obj.role = self.role
        obj.tenant_id = self._added[-1].tenant_id if hasattr(self._added[-1], 'tenant_id') else "t-1"


@pytest.mark.asyncio
async def test_register_new_tenant_derives_role():
    """Email tenant@acme.com → role tenant_admin, tenant 'acme' created."""
    fake_db = _RegSession(tenant_exists=False, role_name="tenant_admin")
    app.dependency_overrides[get_db] = lambda: fake_db

    async def _fake_jwt(user):
        return "mock-token"

    try:
        with patch("backend.app.routers.auth_session.write_jwt", _fake_jwt), \
             patch("backend.app.routers.auth_session.hash_password", return_value="hashed"):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://t") as ac:
                r = await ac.post(
                    "/api/v1/auth/register",
                    json={"email": "tenant@acme.com", "password": "password123"},
                )
        assert r.status_code == 201
        data = r.json()
        assert data["token"] == "mock-token"
        assert data["user"]["role"] == "tenant_admin"
        assert data["user"]["tenant_id"] is not None
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_register_existing_tenant_reused():
    """Email brand@acme.com → existing tenant reused (no new tenant created)."""
    fake_db = _RegSession(tenant_exists=True, role_name="brand_manager")
    app.dependency_overrides[get_db] = lambda: fake_db

    async def _fake_jwt(user):
        return "mock-token"

    try:
        with patch("backend.app.routers.auth_session.write_jwt", _fake_jwt), \
             patch("backend.app.routers.auth_session.hash_password", return_value="hashed"):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://t") as ac:
                r = await ac.post(
                    "/api/v1/auth/register",
                    json={"email": "brand@acme.com", "password": "password123"},
                )
        assert r.status_code == 201
        data = r.json()
        assert data["user"]["role"] == "brand_manager"
        # no new Tenant was added (existing was reused)
        new_tenants = [o for o in fake_db._added if isinstance(o, Tenant)]
        assert len(new_tenants) == 0
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_register_admin_prefix_gets_platform_admin():
    """Email admin@newco.com → role platform_admin, tenant 'newco' created."""
    fake_db = _RegSession(tenant_exists=False, role_name="platform_admin")
    app.dependency_overrides[get_db] = lambda: fake_db

    async def _fake_jwt(user):
        return "mock-token"

    try:
        with patch("backend.app.routers.auth_session.write_jwt", _fake_jwt), \
             patch("backend.app.routers.auth_session.hash_password", return_value="hashed"):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://t") as ac:
                r = await ac.post(
                    "/api/v1/auth/register",
                    json={"email": "admin@newco.com", "password": "password123"},
                )
        assert r.status_code == 201
        assert r.json()["user"]["role"] == "platform_admin"
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_register_duplicate_email_409():
    """Duplicate email returns 409."""
    class _DupSession:
        _call = 0
        async def execute(self, *args, **kwargs):
            result = MagicMock()
            result.scalar_one_or_none.return_value = User.__new__(User)  # existing user
            return result
        def add(self, obj): pass
        async def flush(self): pass
        async def commit(self): pass
        async def refresh(self, obj): pass

    app.dependency_overrides[get_db] = lambda: _DupSession()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as ac:
            r = await ac.post(
                "/api/v1/auth/register",
                json={"email": "tenant@acme.com", "password": "password123"},
            )
        assert r.status_code == 409
    finally:
        app.dependency_overrides.pop(get_db, None)
```

- [ ] **Step 2: Run new backend tests**

```bash
cd D:/staging/ntm
python -m pytest backend/tests/routers/test_auth_session.py -v
```

Expected: All 5 tests pass (1 existing + 4 new).

- [ ] **Step 3: Commit**

```bash
git add backend/tests/routers/test_auth_session.py
git commit -m "test(auth): add register auto-tenant + role derivation tests"
```

---

## Task 3: Mock handler — add `tenant_id` to login + register responses

**Files:**
- Modify: `frontend/src/mocks/handlers/auth.ts`

**Context:** `EMAIL_ROLE_MAP` and `getRoleFromEmail` already exist. Login mock returns `{token, user: {id, email, role}}` — missing `tenant_id`. Register mock same issue. Need `getTenantFromEmail(email): string` helper, and both handlers must include `tenant_id` in user payload.

- [ ] **Step 1: Add `getTenantFromEmail` helper and update both handlers**

Replace the entire content of `frontend/src/mocks/handlers/auth.ts`:

```typescript
import { http, HttpResponse } from 'msw'
import { users } from '../db'

const STORAGE_KEY = 'ntm:registered_emails'

const SEED_EMAILS = new Set(users.map((u) => u.email.toLowerCase()))

const EMAIL_ROLE_MAP: Record<string, string> = {
  admin:    'platform_admin',
  platform: 'platform_admin',
  tenant:   'tenant_admin',
  brand:    'brand_manager',
  cmo:      'cmo',
  creative: 'creative_lead',
  campaign: 'campaign_manager',
  viewer:   'viewer',
}

function getRoleFromEmail(email: string): string {
  const prefix = email.split('@')[0].split('.')[0].toLowerCase()
  return EMAIL_ROLE_MAP[prefix] ?? 'brand_manager'
}

function getTenantFromEmail(email: string): string {
  const domain = email.split('@')[1] ?? 'unknown'
  return domain.split('.')[0].toLowerCase()
}

function isRegistered(email: string): boolean {
  if (SEED_EMAILS.has(email)) return true
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]') as string[]
    return stored.includes(email)
  } catch {
    return false
  }
}

function saveRegistered(email: string): void {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]') as string[]
    if (!stored.includes(email)) {
      stored.push(email)
      localStorage.setItem(STORAGE_KEY, JSON.stringify(stored))
    }
  } catch {
    // localStorage unavailable — skip persistence
  }
}

export const authHandlers = [
  http.post('/api/v1/auth/login', async ({ request }) => {
    const body = await request.json() as { email: string; password: string }
    return HttpResponse.json({
      token: 'mock-jwt-token',
      user: {
        id: `user-${body.email}`,
        email: body.email,
        role: getRoleFromEmail(body.email),
        tenant_id: getTenantFromEmail(body.email),
      },
    })
  }),

  http.post('/api/v1/auth/register', async ({ request }) => {
    const body = await request.json() as { email: string; password: string }
    const email = body.email.toLowerCase().trim()

    if (isRegistered(email)) {
      return HttpResponse.json(
        { detail: 'User already exists' },
        { status: 409 },
      )
    }

    saveRegistered(email)

    return HttpResponse.json({
      token: 'mock-jwt-token',
      user: {
        id: `user-${email}`,
        email: body.email,
        role: getRoleFromEmail(email),
        tenant_id: getTenantFromEmail(email),
      },
    }, { status: 201 })
  }),
]
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/mocks/handlers/auth.ts
git commit -m "feat(mock): add tenant_id to login+register mock responses"
```

---

## Task 4: Frontend — live role/tenant preview badge in register form

**Files:**
- Modify: `frontend/src/pages/Login/LoginPage.tsx`

**Context:** `RegisterForm` uses `react-hook-form` with `useWatch` or `watch`. Add a `parseEmailIdentity` utility inline that returns `{role, tenant} | null`. Show a badge under the email field only when `@domain` is present. Keep login form untouched.

- [ ] **Step 1: Add `parseEmailIdentity` helper and badge to `RegisterForm`**

Replace the entire `frontend/src/pages/Login/LoginPage.tsx`:

```tsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/store/useAuthStore'
import { login as loginApi, register as registerApi } from '@/api/admin'

// ── Email identity parsing ────────────────────────────────────────────────────

const EMAIL_ROLE_MAP: Record<string, string> = {
  admin:    'Platform Admin',
  platform: 'Platform Admin',
  tenant:   'Tenant Admin',
  brand:    'Brand Manager',
  cmo:      'CMO',
  creative: 'Creative Lead',
  campaign: 'Campaign Manager',
  viewer:   'Viewer',
}

function parseEmailIdentity(email: string): { role: string; tenant: string } | null {
  if (!email.includes('@')) return null
  const [local, domain] = email.toLowerCase().split('@')
  if (!domain || !domain.includes('.')) return null
  const prefix = local.split('.')[0]
  const tenant = domain.split('.')[0]
  if (!tenant) return null
  const role = EMAIL_ROLE_MAP[prefix] ?? 'Brand Manager'
  return { role, tenant }
}

// ── Schemas ───────────────────────────────────────────────────────────────────

const loginSchema = z.object({
  email: z.string().email('Enter a valid email'),
  password: z.string().min(1, 'Password is required'),
})

const registerSchema = z.object({
  email: z.string().email('Enter a valid email'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  confirmPassword: z.string().min(1, 'Please confirm your password'),
}).refine((data) => data.password === data.confirmPassword, {
  message: 'Passwords do not match',
  path: ['confirmPassword'],
})

type LoginFormValues = z.infer<typeof loginSchema>
type RegisterFormValues = z.infer<typeof registerSchema>

// ── Login Form ────────────────────────────────────────────────────────────────

function LoginForm({ onSwitch }: { onSwitch: () => void }) {
  const navigate = useNavigate()
  const { login } = useAuthStore()
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '' },
  })

  const onSubmit = async (data: LoginFormValues) => {
    setError(null)
    setLoading(true)
    try {
      const result = await loginApi(data.email, data.password)
      login(result.token, result.user)
      navigate('/admin/onboarding')
    } catch {
      setError('Invalid email or password.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl>
                <Input type="email" placeholder="e.g. tenant@yourcompany.com" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Password</FormLabel>
              <FormControl>
                <Input type="password" placeholder="••••••••" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        {error && <p className="text-sm text-destructive">{error}</p>}
        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? 'Signing in…' : 'Sign in'}
        </Button>
        <p className="text-center text-sm text-muted-foreground">
          Don't have an account?{' '}
          <button
            type="button"
            onClick={onSwitch}
            className="text-primary font-medium hover:underline"
          >
            Register
          </button>
        </p>
      </form>
    </Form>
  )
}

// ── Register Form ─────────────────────────────────────────────────────────────

function RegisterForm({ onSwitch }: { onSwitch: () => void }) {
  const navigate = useNavigate()
  const { login } = useAuthStore()
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const form = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { email: '', password: '', confirmPassword: '' },
  })

  const emailValue = useWatch({ control: form.control, name: 'email' })
  const identity = parseEmailIdentity(emailValue ?? '')

  const onSubmit = async (data: RegisterFormValues) => {
    setError(null)
    setLoading(true)
    try {
      const result = await registerApi(data.email, data.password)
      login(result.token, result.user)
      navigate('/admin/onboarding')
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail
      if (detail === 'User already exists') {
        setError('An account with this email already exists. Please sign in instead.')
      } else {
        setError('Registration failed. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl>
                <Input type="email" placeholder="e.g. tenant@yourcompany.com" {...field} />
              </FormControl>
              {identity && (
                <p className="text-xs text-muted-foreground mt-1">
                  <span className="font-medium text-foreground">Role:</span> {identity.role}
                  {' · '}
                  <span className="font-medium text-foreground">Tenant:</span> {identity.tenant}
                </p>
              )}
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Password</FormLabel>
              <FormControl>
                <Input type="password" placeholder="••••••••" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="confirmPassword"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Confirm Password</FormLabel>
              <FormControl>
                <Input type="password" placeholder="••••••••" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        {error && <p className="text-sm text-destructive">{error}</p>}
        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? 'Creating account…' : 'Create account'}
        </Button>
        <p className="text-center text-sm text-muted-foreground">
          Already have an account?{' '}
          <button
            type="button"
            onClick={onSwitch}
            className="text-primary font-medium hover:underline"
          >
            Sign in
          </button>
        </p>
      </form>
    </Form>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export function LoginPage() {
  const [mode, setMode] = useState<'login' | 'register'>('login')

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <Card className="w-full max-w-sm shadow-lg">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">NTM</CardTitle>
          <p className="text-sm text-muted-foreground">
            {mode === 'login' ? 'Sign in to your account' : 'Create a new account'}
          </p>
        </CardHeader>
        <CardContent>
          {mode === 'login'
            ? <LoginForm onSwitch={() => setMode('register')} />
            : <RegisterForm onSwitch={() => setMode('login')} />
          }
        </CardContent>
      </Card>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Login/LoginPage.tsx
git commit -m "feat(login): live role/tenant preview badge on register form"
```

---

## Task 5: Frontend tests — role preview badge

**Files:**
- Modify: `frontend/src/test/login.test.tsx`

**Context:** Uses `renderWithProviders` + `@testing-library/react`. Need `userEvent` for typing into the email field. MSW is set up in test environment. Test that typing `tenant@acme.com` in register mode shows "Role: Tenant Admin · Tenant: acme".

- [ ] **Step 1: Add role preview tests**

Replace the entire `frontend/src/test/login.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest'
import { screen, fireEvent } from '@testing-library/react'
import { renderWithProviders } from './utils'
import { LoginPage } from '@/pages/Login/LoginPage'

describe('LoginPage', () => {
  it('renders without crashing', () => {
    renderWithProviders(<LoginPage />, { route: '/login', path: '/login' })
    expect(document.body).toBeInTheDocument()
  })

  it('shows email input', () => {
    renderWithProviders(<LoginPage />, { route: '/login', path: '/login' })
    const emailInput =
      screen.queryByRole('textbox', { name: /email/i }) ??
      screen.queryByPlaceholderText(/email/i) ??
      document.querySelector('input[type="email"]')
    expect(emailInput).toBeTruthy()
  })

  it('shows password input', () => {
    renderWithProviders(<LoginPage />, { route: '/login', path: '/login' })
    const passwordInput = document.querySelector('input[type="password"]')
    expect(passwordInput).toBeTruthy()
  })

  it('shows submit button', () => {
    renderWithProviders(<LoginPage />, { route: '/login', path: '/login' })
    const btn =
      screen.queryByRole('button', { name: /sign in|log in|login|submit/i }) ??
      document.querySelector('button[type="submit"]')
    expect(btn).toBeTruthy()
  })
})

describe('LoginPage — register mode role preview', () => {
  it('shows no preview when email has no domain', () => {
    renderWithProviders(<LoginPage />, { route: '/login', path: '/login' })
    // switch to register mode
    const registerLink = screen.getByRole('button', { name: /register/i })
    fireEvent.click(registerLink)

    const emailInput = document.querySelector('input[type="email"]')!
    fireEvent.change(emailInput, { target: { value: 'tenant' } })

    expect(screen.queryByText(/Role:/i)).toBeNull()
  })

  it('shows Tenant Admin + tenant name when email is tenant@acme.com', () => {
    renderWithProviders(<LoginPage />, { route: '/login', path: '/login' })
    const registerLink = screen.getByRole('button', { name: /register/i })
    fireEvent.click(registerLink)

    const emailInput = document.querySelector('input[type="email"]')!
    fireEvent.change(emailInput, { target: { value: 'tenant@acme.com' } })

    expect(screen.getByText(/Tenant Admin/i)).toBeInTheDocument()
    expect(screen.getByText(/acme/i)).toBeInTheDocument()
  })

  it('shows Platform Admin for admin@newco.com', () => {
    renderWithProviders(<LoginPage />, { route: '/login', path: '/login' })
    const registerLink = screen.getByRole('button', { name: /register/i })
    fireEvent.click(registerLink)

    const emailInput = document.querySelector('input[type="email"]')!
    fireEvent.change(emailInput, { target: { value: 'admin@newco.com' } })

    expect(screen.getByText(/Platform Admin/i)).toBeInTheDocument()
    expect(screen.getByText(/newco/i)).toBeInTheDocument()
  })

  it('defaults to Brand Manager for unknown prefix', () => {
    renderWithProviders(<LoginPage />, { route: '/login', path: '/login' })
    const registerLink = screen.getByRole('button', { name: /register/i })
    fireEvent.click(registerLink)

    const emailInput = document.querySelector('input[type="email"]')!
    fireEvent.change(emailInput, { target: { value: 'randomuser@startup.io' } })

    expect(screen.getByText(/Brand Manager/i)).toBeInTheDocument()
    expect(screen.getByText(/startup/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run frontend tests**

```bash
cd D:/staging/ntm/frontend
npx vitest run src/test/login.test.tsx
```

Expected: All 8 tests pass.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/test/login.test.tsx
git commit -m "test(login): add role preview badge tests for register form"
```

---

## Self-Review

**Spec coverage:**
- ✅ Email prefix → role: `_parse_email` + `_EMAIL_ROLE_MAP` in backend; `parseEmailIdentity` in frontend
- ✅ Domain → tenant slug: both backend and frontend
- ✅ Auto-create tenant if new: `flush()` + INSERT in register endpoint
- ✅ Reuse existing tenant: SELECT before INSERT
- ✅ Login works for any registered user: login endpoint untouched
- ✅ Live preview badge: `useWatch` + `identity &&` conditional render
- ✅ Mock returns `tenant_id`: both login + register handlers updated
- ✅ `tenant_id` in `useAuthStore.AuthUser`: already has `tenant_id?: string`

**Placeholder scan:** None found.

**Type consistency:**
- `result.user` from API includes `tenant_id` — `AuthUser` in `useAuthStore` has `tenant_id?: string` ✓
- `registerApi` returns `{ token, user }` — `LoginPage` consumes `.token` + `.user` ✓
- `_parse_email` returns `tuple[str, str]` → used as `role_name, tenant_slug` ✓
