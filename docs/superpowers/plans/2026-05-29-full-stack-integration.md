# Full-Stack Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the React frontend run against the live FastAPI backend with no MSW mocks — real auth, tenant-scoped data persisting in Postgres/Mongo, and Celery agent tasks executing with all external calls stubbed.

**Architecture:** Backend is canonical. We fix the broken auth/tenant layer first (middleware loads the JWT user into `request.state`; a redefined `current_user` dependency reads it), add JSON `/auth/login` + `/auth/register`, seed data, add the few missing list/onboarding routes, then adapt the frontend (`api/admin.ts`, types, hooks) to the real routes. A single `NTM_STUB_EXTERNAL` flag short-circuits all outbound LLM/ad-platform calls. Frontend runs on the Vite dev server with a proxy to `:8000`.

**Tech Stack:** FastAPI, fastapi-users (JWT), SQLAlchemy async (Postgres) + Motor (Mongo), PyJWT, passlib/bcrypt, Celery/Redis, React 18 + Vite + axios + zustand + React Query, MSW (gated off), pytest, vitest.

**Specs:** `docs/superpowers/specs/2026-05-29-full-stack-integration-design.md` (+ `-audit.md`).

**Conventions used throughout:**
- Seed tenant id: `tenant-acme`. Dev password: `devpass123`. Seed emails: `admin@acme.test`, `tenant@acme.test`, `brand@acme.test`, `cmo@acme.test`, `creative@acme.test`, `campaign@acme.test`, `viewer@acme.test`.
- Run backend tests in-container: `docker exec ntm-api pytest <args>`. Run a single test: append `::test_name -v`.
- After backend code changes, reload: `docker compose restart ntm-api ntm-agent-worker` (the image mounts code via COPY, so for code picked up at runtime you may instead rebuild: `docker compose up -d --build ntm-api ntm-agent-worker`). Prefer rebuild when in doubt.
- Commit format (project rule): `[TASK-XXX] action: description` with `Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>`. Use `[FULLSTACK]` as the tag here. Work on branch `feature/audit`. Never commit to `main`.

---

## Phase 0 — Auth & tenant resolution

Outcome: a logged-in, tenant-scoped request succeeds end-to-end.

### Task 1: Auth helper — shared password context + user loader

**Files:**
- Create: `backend/app/core/auth_helpers.py`
- Test: `backend/tests/core/test_auth_helpers.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/core/test_auth_helpers.py
from backend.app.core.auth_helpers import pwd_context, hash_password, verify_password

def test_hash_and_verify_roundtrip():
    hashed = hash_password("devpass123")
    assert hashed != "devpass123"
    assert verify_password("devpass123", hashed) is True
    assert verify_password("wrong", hashed) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker exec ntm-api pytest backend/tests/core/test_auth_helpers.py -v`
Expected: FAIL (module not found). Create `backend/tests/core/__init__.py` if the package import fails.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/core/auth_helpers.py
"""Shared password hashing/verification (bcrypt)."""
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(raw: str) -> str:
    return pwd_context.hash(raw)

def verify_password(raw: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(raw, hashed)
    except Exception:
        return False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker exec ntm-api pytest backend/tests/core/test_auth_helpers.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/auth_helpers.py backend/tests/core/
git commit -m "[FULLSTACK] feat: add shared password hashing helpers"
```

---

### Task 2: Rework `current_user` dependency to read `request.state.user`

The fastapi-users dependency chain is not wired (`get_user_db` has no session `Depends`, no `get_user_manager`). Route guards must instead read the user the middleware will load.

**Files:**
- Modify: `backend/app/core/dependencies.py`
- Test: `backend/tests/core/test_current_user_dependency.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/core/test_current_user_dependency.py
import pytest
from types import SimpleNamespace
from fastapi import HTTPException
from backend.app.core.dependencies import current_user, get_current_tenant

class _Req:
    def __init__(self, **state):
        self.state = SimpleNamespace(**state)

@pytest.mark.asyncio
async def test_current_user_returns_state_user():
    user = SimpleNamespace(id="u1", email="a@b.c")
    assert await current_user(_Req(user=user)) is user

@pytest.mark.asyncio
async def test_current_user_missing_raises_401():
    with pytest.raises(HTTPException) as exc:
        await current_user(_Req())
    assert exc.value.status_code == 401

@pytest.mark.asyncio
async def test_get_current_tenant_reads_state():
    assert await get_current_tenant(_Req(tenant_id="tenant-acme")) == "tenant-acme"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker exec ntm-api pytest backend/tests/core/test_current_user_dependency.py -v`
Expected: FAIL (current_user is a fastapi-users dependency, signature mismatch).

- [ ] **Step 3: Write minimal implementation**

Replace the top of `backend/app/core/dependencies.py` (keep `require_role` and `get_current_user_with_tenant`, but they now use the new `current_user`):

```python
"""FastAPI dependency injection for tenant context and current user."""
from contextvars import ContextVar
from fastapi import Depends, HTTPException, Request
from backend.app.core.models import User, UserRole

tenant_context: ContextVar[str | None] = ContextVar('tenant_id', default=None)


async def current_user(request: Request) -> User:
    """Return the user loaded by TenantValidationMiddleware (request.state.user)."""
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail={"error_code": "INVALID_TOKEN", "message": "Not authenticated"})
    return user


async def get_current_tenant(request: Request) -> str | None:
    """Inject tenant_id resolved by the middleware (request.state), context fallback."""
    return getattr(request.state, "tenant_id", None) or tenant_context.get()


async def get_current_user_with_tenant(
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> tuple[User, str]:
    return user, tenant_id


def require_role(allowed_roles: list[UserRole]):
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

- [ ] **Step 4: Run test to verify it passes**

Run: `docker exec ntm-api pytest backend/tests/core/test_current_user_dependency.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/dependencies.py backend/tests/core/test_current_user_dependency.py
git commit -m "[FULLSTACK] refactor: current_user reads request.state, tenant from state"
```

---

### Task 3: Middleware authenticates JWT and loads user + allowed tenants

**Files:**
- Modify: `backend/app/core/middleware.py`
- Create: `backend/app/core/auth_state.py` (token decode + user load, unit-testable)
- Test: `backend/tests/core/test_auth_state.py`

- [ ] **Step 1: Write the failing test** (decode logic; DB load is integration-tested in Task 8)

```python
# backend/tests/core/test_auth_state.py
import jwt
from backend.app.core.auth_state import decode_user_id
from backend.app.core.config import settings

def _make_token(sub):
    return jwt.encode(
        {"sub": sub, "aud": ["fastapi-users:auth"]},
        settings.SECRET_KEY, algorithm=settings.ALGORITHM,
    )

def test_decode_user_id_ok():
    assert decode_user_id(_make_token("user-123")) == "user-123"

def test_decode_user_id_bad_token():
    assert decode_user_id("garbage") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker exec ntm-api pytest backend/tests/core/test_auth_state.py -v`
Expected: FAIL (module missing).

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/core/auth_state.py
"""Decode fastapi-users JWTs and load the user with role + allowed tenants."""
import jwt
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from backend.app.core.config import settings
from backend.app.core.models import User, user_tenant_access

_AUDIENCE = "fastapi-users:auth"


def decode_user_id(token: str) -> str | None:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM], audience=_AUDIENCE,
        )
        return payload.get("sub")
    except Exception:
        return None


async def load_user_and_tenants(session, user_id: str):
    """Return (user, allowed_tenant_ids) or (None, []) if not found."""
    result = await session.execute(
        select(User).where(User.id == user_id).options(selectinload(User.role))
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        return None, []
    allowed = {user.tenant_id}
    rows = await session.execute(
        select(user_tenant_access.c.tenant_id).where(user_tenant_access.c.user_id == user_id)
    )
    allowed.update(r[0] for r in rows.all())
    return user, list(allowed)
```

Then rewrite `backend/app/core/middleware.py`:

```python
"""Tenant validation middleware: authenticates JWT, validates X-Tenant-ID."""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from backend.app.core.auth_state import decode_user_id, load_user_and_tenants
from backend.app.core.dependencies import tenant_context
from backend.app.core.exceptions import (
    MissingTenantHeaderException, TenantMismatchException, InvalidTokenException,
)
from backend.app.db import get_session_local

PUBLIC_PATHS = {
    "/health", "/docs", "/openapi.json", "/redoc",
    "/api/v1/auth/login", "/api/v1/auth/register", "/api/v1/auth/jwt/login",
    "/api/v1/auth/password-reset/request", "/api/v1/auth/password-reset/confirm",
}


class TenantValidationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)
        try:
            auth = request.headers.get("Authorization", "")
            token = auth[7:] if auth.lower().startswith("bearer ") else None
            user_id = decode_user_id(token) if token else None
            if not user_id:
                raise InvalidTokenException()

            factory = get_session_local()
            async with factory() as session:
                user, allowed = await load_user_and_tenants(session, user_id)
            if user is None:
                raise InvalidTokenException()

            request.state.user = user
            request.state.allowed_tenants = allowed

            tenant_id = request.headers.get("X-Tenant-ID")
            if not tenant_id:
                raise MissingTenantHeaderException()
            if tenant_id not in allowed:
                raise TenantMismatchException(tenant_id)

            request.state.tenant_id = tenant_id
            tenant_context.set(tenant_id)
            return await call_next(request)
        except Exception as exc:
            if hasattr(exc, "status_code") and hasattr(exc, "detail"):
                return JSONResponse(status_code=exc.status_code, content=exc.detail)
            raise
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker exec ntm-api pytest backend/tests/core/test_auth_state.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/auth_state.py backend/app/core/middleware.py backend/tests/core/test_auth_state.py
git commit -m "[FULLSTACK] feat: middleware authenticates JWT and loads user/tenants"
```

---

### Task 4: JSON `/auth/login` and `/auth/register` returning frontend shape

**Files:**
- Create: `backend/app/routers/auth_session.py`
- Modify: `backend/app/routers/__init__.py` (register the router)
- Modify: `backend/app/core/auth.py` (export a token writer helper — see step 3)
- Test: `backend/tests/routers/test_auth_session.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/routers/test_auth_session.py
import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app

@pytest.mark.asyncio
async def test_login_unknown_user_401(monkeypatch):
    # No DB user -> 401. (Full happy-path covered by integration smoke, Task 14.)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as ac:
        r = await ac.post("/api/v1/auth/login", json={"email": "nobody@x.com", "password": "x"})
    assert r.status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker exec ntm-api pytest backend/tests/routers/test_auth_session.py -v`
Expected: FAIL (404 — route does not exist).

- [ ] **Step 3: Write minimal implementation**

Add to `backend/app/core/auth.py`:

```python
async def write_jwt(user) -> str:
    """Mint a JWT readable by the auth middleware."""
    return await get_jwt_strategy().write_token(user)
```

Create `backend/app/routers/auth_session.py`:

```python
"""JSON session auth: POST /api/v1/auth/login and /register (frontend contract)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.auth import write_jwt
from backend.app.core.auth_helpers import hash_password, verify_password
from backend.app.core.models import User, Role
from backend.app.db import get_db

router = APIRouter(prefix="/api/v1/auth", tags=["auth-session"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_id: str | None = None
    role: str | None = None


def _user_payload(user: User, token: str) -> dict:
    return {
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role.name if user.role else None,
            "tenant_id": user.tenant_id,
        },
    }


@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(
        select(User).where(User.email == body.email).options(selectinload(User.role))
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail={"error_code": "INVALID_CREDENTIALS", "message": "Invalid email or password"})
    token = await write_jwt(user)
    return _user_payload(user, token)


@router.post("/register", status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)) -> dict:
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail={"error_code": "USER_EXISTS", "message": "User already exists"})

    role_name = body.role or "brand_manager"
    role_row = (await db.execute(select(Role).where(Role.name == role_name))).scalar_one_or_none()
    if role_row is None:
        raise HTTPException(status_code=400, detail={"error_code": "BAD_ROLE", "message": f"Unknown role {role_name}"})

    tenant_id = body.tenant_id or "tenant-acme"
    user = User(
        email=body.email, hashed_password=hash_password(body.password),
        tenant_id=tenant_id, role_id=role_row.id, is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    user.role = role_row
    token = await write_jwt(user)
    return _user_payload(user, token)
```

Register the router in `backend/app/routers/__init__.py`:

```python
from backend.app.routers.auth_session import router as auth_session_router
# ... inside register_routers(app):
    app.include_router(auth_session_router)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker exec ntm-api pytest backend/tests/routers/test_auth_session.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/auth_session.py backend/app/routers/__init__.py backend/app/core/auth.py backend/tests/routers/test_auth_session.py
git commit -m "[FULLSTACK] feat: JSON /auth/login and /auth/register"
```

---

### Task 5: Fix Mongo env var mismatch

**Files:**
- Modify: `backend/app/routers/campaign.py:38-42` (and any sibling using `MONGO_DB_URL`)

- [ ] **Step 1: Find all occurrences**

Run (Grep tool): pattern `MONGO_DB_URL|MONGO_DB_NAME` across `backend/app`.
Expected: `campaign.py` `get_db` (and possibly creatives/creative_director).

- [ ] **Step 2: Edit each `get_db` to read the compose var names**

```python
async def get_db() -> AsyncIOMotorDatabase:
    mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    mongo_db_name = os.getenv("MONGODB_DB", "ntm")
    client = AsyncIOMotorClient(mongo_url)
    return client[mongo_db_name]
```

- [ ] **Step 3: Add `MONGODB_DB` to compose** for `ntm-api` and `ntm-agent-worker` (in `docker-compose.yml` environment blocks): `MONGODB_DB: ntm`.

- [ ] **Step 4: Verify** import still loads: `docker exec ntm-api python -c "import backend.app.routers.campaign"` → no error.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/campaign.py docker-compose.yml
git commit -m "[FULLSTACK] fix: use MONGODB_URL/MONGODB_DB env names for Mongo"
```

---

### Task 6: Frontend — Vite proxy, MSW gate, X-Tenant-ID interceptor

**Files:**
- Modify: `frontend/vite.config.ts`
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/src/api/client.ts`
- Create: `frontend/.env.development` (sets `VITE_USE_MOCKS=false`)

- [ ] **Step 1: Add the dev proxy** — `frontend/vite.config.ts`:

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  server: {
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/health': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
```

- [ ] **Step 2: Gate MSW behind an env flag** — `frontend/src/main.tsx`, replace `enableMocking`:

```ts
async function enableMocking() {
  if (import.meta.env.VITE_USE_MOCKS !== 'true') return
  const { worker } = await import('./mocks/browser')
  return worker.start({ onUnhandledRequest: 'bypass' })
}
```

- [ ] **Step 3: Attach X-Tenant-ID** — `frontend/src/api/client.ts`, extend the request interceptor:

```ts
apiClient.interceptors.request.use((config) => {
  const { token, user } = useAuthStore.getState()
  if (token) config.headers.Authorization = `Bearer ${token}`
  if (user?.tenant_id) config.headers['X-Tenant-ID'] = user.tenant_id
  return config
})
```

- [ ] **Step 4: Create `frontend/.env.development`:**

```
VITE_USE_MOCKS=false
```

- [ ] **Step 5: Verify build/typecheck**

Run: `cd frontend && npx tsc -b --noEmit`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/vite.config.ts frontend/src/main.tsx frontend/src/api/client.ts frontend/.env.development
git commit -m "[FULLSTACK] feat: vite proxy, MSW gate off, X-Tenant-ID header"
```

---

## Phase 1 — Seed data

### Task 7: Idempotent seed script

**Files:**
- Create: `backend/app/scripts/__init__.py`
- Create: `backend/app/scripts/seed.py`
- Test: `backend/tests/scripts/test_seed.py`

- [ ] **Step 1: Write the failing test** (uses the in-memory sqlite engine from the test conftest fixture `db_session`; if no such fixture exists, see `backend/tests/services/test_mandate_service.py` for the existing pattern and reuse it)

```python
# backend/tests/scripts/test_seed.py
import pytest
from sqlalchemy import select, func
from backend.app.scripts.seed import seed_all
from backend.app.core.models import User, Role, Tenant

@pytest.mark.asyncio
async def test_seed_is_idempotent(db_session):
    await seed_all(db_session)
    await seed_all(db_session)  # second run must not duplicate
    roles = (await db_session.execute(select(func.count()).select_from(Role))).scalar()
    tenants = (await db_session.execute(select(func.count()).select_from(Tenant))).scalar()
    users = (await db_session.execute(select(func.count()).select_from(User))).scalar()
    assert roles == 7
    assert tenants >= 1
    assert users == 7
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker exec ntm-api pytest backend/tests/scripts/test_seed.py -v`
Expected: FAIL (module missing). Create `backend/tests/scripts/__init__.py`.

- [ ] **Step 3: Write the implementation**

```python
# backend/app/scripts/seed.py
"""Idempotent dev seed: roles, one tenant, one user per role, a sample mandate."""
import asyncio
import uuid
from sqlalchemy import select
from backend.app.core.config import DEFAULT_RBAC_ROLES
from backend.app.core.models import User, Role, Tenant
from backend.app.core.auth_helpers import hash_password
from backend.app.db import get_session_local

TENANT_ID = "tenant-acme"
DEV_PASSWORD = "devpass123"
EMAIL_BY_ROLE = {
    "platform_admin": "admin@acme.test",
    "tenant_admin": "tenant@acme.test",
    "brand_manager": "brand@acme.test",
    "cmo": "cmo@acme.test",
    "creative_lead": "creative@acme.test",
    "campaign_manager": "campaign@acme.test",
    "viewer": "viewer@acme.test",
}


async def _get_or_create_role(session, name, perms):
    row = (await session.execute(select(Role).where(Role.name == name))).scalar_one_or_none()
    if row is None:
        row = Role(id=str(uuid.uuid4()), name=name, permissions=perms)
        session.add(row)
        await session.flush()
    return row


async def seed_all(session):
    # Tenant
    tenant = (await session.execute(select(Tenant).where(Tenant.id == TENANT_ID))).scalar_one_or_none()
    if tenant is None:
        session.add(Tenant(id=TENANT_ID, name="Acme", is_active=True))
        await session.flush()
    # Roles + users
    for role_name, perms in DEFAULT_RBAC_ROLES.items():
        role = await _get_or_create_role(session, role_name, perms)
        email = EMAIL_BY_ROLE[role_name]
        existing = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if existing is None:
            session.add(User(
                id=str(uuid.uuid4()), email=email,
                hashed_password=hash_password(DEV_PASSWORD),
                tenant_id=TENANT_ID, role_id=role.id, is_active=True,
            ))
    await session.commit()


async def _main():
    factory = get_session_local()
    async with factory() as session:
        await seed_all(session)
    print("Seed complete: tenant=%s, users=%d" % (TENANT_ID, len(EMAIL_BY_ROLE)))


if __name__ == "__main__":
    asyncio.run(_main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker exec ntm-api pytest backend/tests/scripts/test_seed.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/scripts/ backend/tests/scripts/
git commit -m "[FULLSTACK] feat: idempotent dev seed script"
```

---

### Task 8: Integration — login against the real DB

**Files:**
- Modify: `docker-compose.yml` (add `MONGODB_DB` done in Task 5; nothing else)
- Manual verification (no new test file; this proves Tasks 1–7 together).

- [ ] **Step 1: Rebuild + restart backend**

```bash
docker compose up -d --build ntm-api ntm-agent-worker
```

- [ ] **Step 2: Seed the running DB**

```bash
docker exec ntm-api python -m backend.app.scripts.seed
```
Expected: `Seed complete: tenant=tenant-acme, users=7`

- [ ] **Step 3: Login via the real API** (use the context-mode JS fetch helper, since curl is blocked):
Fetch `POST http://localhost:8000/api/v1/auth/login` with body `{"email":"admin@acme.test","password":"devpass123"}`.
Expected: 200, JSON `{ token, user: { id, email, role: "platform_admin", tenant_id: "tenant-acme" } }`.

- [ ] **Step 4: Call a protected route** with `Authorization: Bearer <token>` + `X-Tenant-ID: tenant-acme`:
`GET http://localhost:8000/api/v1/mandates/does-not-exist` → expect **404** (auth+tenant passed; resource missing), NOT 401/400.
Without `X-Tenant-ID` → **400**. With a bad token → **401**.

- [ ] **Step 5: Commit** (only if compose changed and not already committed)

```bash
git commit -am "[FULLSTACK] chore: verify real-DB login + protected route" --allow-empty
```

---

## Phase 2 — Missing routes

### Task 9: `GET /api/v1/mandates` (list, tenant-scoped)

**Files:**
- Modify: `backend/app/services/mandate_service.py` (add `list`)
- Modify: `backend/app/routers/mandate.py` (add route)
- Test: `backend/tests/services/test_mandate_service.py` (add a list test, following existing tests in this file)

- [ ] **Step 1: Write the failing test** (mirror the create/get tests already in the file)

```python
@pytest.mark.asyncio
async def test_list_returns_only_tenant_mandates(db_session):
    svc = MandateService(db_session)
    await svc.create(_make_create_request(name="A"), user_id="u1", tenant_id="t1")
    await svc.create(_make_create_request(name="B"), user_id="u1", tenant_id="t2")
    rows = await svc.list("t1")
    assert len(rows) == 1
    assert rows[0]["name"] == "A"
```
(`_make_create_request` — reuse the helper/fixture already used by this test file for `create`.)

- [ ] **Step 2: Run** `docker exec ntm-api pytest backend/tests/services/test_mandate_service.py -k list -v` → FAIL.

- [ ] **Step 3: Implement** — add to `MandateService`:

```python
    async def list(self, tenant_id: str) -> list[dict]:
        result = await self._db.execute(
            select(Mandate).where(Mandate.tenant_id == tenant_id).order_by(Mandate.id)
        )
        return [m.to_dict() for m in result.scalars().all()]
```

Add to `backend/app/routers/mandate.py` (follow the auth/tenant/db deps used by the existing `GET /mandates/{id}` handler in that file):

```python
@router.get("/mandates", status_code=200)
async def list_mandates(
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    return await MandateService(db).list(tenant_id)
```

- [ ] **Step 4: Run** the test → PASS. Also `docker exec ntm-api pytest backend/tests/routers/test_mandate_router.py -v` → still PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/mandate_service.py backend/app/routers/mandate.py backend/tests/services/test_mandate_service.py
git commit -m "[FULLSTACK] feat: list mandates endpoint (tenant-scoped)"
```

---

### Task 10: `GET /api/v1/campaigns` (list, tenant-scoped)

**Files:**
- Modify: `backend/app/services/campaign_service.py` (add `list`)
- Modify: `backend/app/routers/campaign.py` (add route)
- Test: `backend/tests/services/test_campaign_service.py` (add a list test, following existing async-mongo mock pattern in this file)

- [ ] **Step 1: Write the failing test** — follow the existing mocked-Motor pattern in this file (it already mocks `db["campaigns"]`). Assert `list` calls `find({"tenant_id": ...})` and serializes each doc with the same `_id → id` mapping used by `get`.

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement** — add to `CampaignService` (reuse the existing doc→response serializer used by `get`; it maps `_id` to `id`):

```python
    async def list(self, tenant_id: str) -> list[dict]:
        cursor = self._campaigns.find({"tenant_id": tenant_id})
        docs = await cursor.to_list(length=None)
        return [self._serialize(doc) for doc in docs]
```
If the existing class names its serializer differently than `_serialize`, use that name (check how `get` builds its `CampaignResponse`). If `get` builds the response inline, extract that mapping into `_serialize(doc)` and reuse it in both.

Add to `backend/app/routers/campaign.py` (mirror existing campaign route deps):

```python
@router.get("/campaigns", status_code=200)
async def list_campaigns(
    _: User = Depends(require_role(CAMPAIGN_ROLES)),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list:
    return await CampaignService(db).list(tenant_id)
```

- [ ] **Step 4: Run** the campaign service + router tests → PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/campaign_service.py backend/app/routers/campaign.py backend/tests/services/test_campaign_service.py
git commit -m "[FULLSTACK] feat: list campaigns endpoint (tenant-scoped)"
```

---

## Phase 3 — Reconcile frontend to backend (backend canonical)

Each item adapts `frontend/src/api/admin.ts` / `frontend/src/types/admin.ts` / hooks to the real backend route or shape. After each change, run `cd frontend && npx tsc -b --noEmit` then exercise the page on `:5173`. Group into one commit per logical area.

### Task 11: Reconcile admin + mandate + analytics paths/shapes

**Files:**
- Modify: `frontend/src/api/admin.ts`
- Modify: `frontend/src/types/admin.ts` (align types to backend `response_model`s)
- Modify affected hooks under `frontend/src/hooks/` and pages where a call signature changes.

- [ ] **Step 1: Audit-log path + params.** Change `getAuditLog` to call `/admin/audit-log` and map params to the backend's (`AuditLogResponse`). Open `backend/app/routers/admin.py:130` to read the exact query params + response fields; align `AuditFilters` and the `AuditLog` type to them.

- [ ] **Step 2: Users + tenants admin.** Repoint to real routes:
  - `createUser`: `POST /admin/users` with the body the backend expects (read `backend/app/routers/admin.py:65`); drop the `tenantId` path segment.
  - User role change: replace `deactivateUser`(`PATCH /admin/users/{id}`) usage with `PUT /admin/users/{id}/role` where the UI changes a role; if the UI only deactivates and the backend has no deactivate route, remove the deactivate affordance (backend-canonical) and note it in the page.
  - `toggleTenant` / `getUsersByTenant`: no backend equivalents — remove these UI affordances or hide them behind a "not implemented" guard; do not invent backend routes.
  - `getRoles`: backend has no `/admin/roles`. Replace the Roles page data source with the static `UserRole` set (render the known roles) OR hide the page. Decide here: **render static roles** from a shared constant `ROLE_NAMES` in `frontend/src/lib/roles.ts`.
  - `getHealth` (`/admin/health`): repoint to the top-level `GET /health` (returns `{status:"ok"}`) and adjust the Health page to that shape, or hide richer health UI.

- [ ] **Step 3: Mandate update method.** Change `updateMandate` from `PATCH` to `PUT /mandates/{id}` (backend uses PUT). Confirm request body matches `UpdateMandateRequest` (`backend/app/schemas/mandate.py`).

- [ ] **Step 4: Analytics.** Replace `getAnalyticsSummary`/`getAnalyticsTrends` with the backend analytics routes:
  - Summary/dashboard → `GET /analytics/dashboard` (read `backend/app/routers/analytics.py:79` for params + shape).
  - KPI status → `GET /analytics/kpi-status`.
  - Channel performance → `GET /analytics/channel-performance`.
  Update `useAnalytics.ts` and the Analytics/KPI pages' data mappers to the real shapes (align the chart-data transforms in `AnalyticsPage.tsx` / `KPIDashboardPage.tsx`).

- [ ] **Step 5: Typecheck + commit**

```bash
cd frontend && npx tsc -b --noEmit
git add frontend/src/api/admin.ts frontend/src/types/admin.ts frontend/src/hooks frontend/src/lib frontend/src/pages
git commit -m "[FULLSTACK] refactor: adapt admin/mandate/analytics calls to backend routes"
```

### Task 12: Reconcile campaign + creatives + KPI-config paths

**Files:**
- Modify: `frontend/src/api/admin.ts`, `frontend/src/hooks/useCampaigns.ts`, `frontend/src/hooks/useCreatives.ts`, affected campaign pages.

- [ ] **Step 1: Campaign KPIs.** `getCampaignKpis` (`/campaigns/{id}/kpis`) → `GET /campaigns/{id}/analytics` (read `backend/app/routers/analytics.py:56`). Map the KPIs page to that shape.

- [ ] **Step 2: KPI configs.** `updateKpiConfig` (`/campaigns/{id}/kpi-configs/...`) has no backend route. Remove the inline-edit affordance on the KPIs page (backend-canonical) or render values read-only. Do not invent a backend route.

- [ ] **Step 3: Confirm-concept body.** Align `confirmConcept` body to backend `CampaignConfirmRequest` (read `backend/app/schemas/campaign.py`); update the Concepts page call.

- [ ] **Step 4: Alerts.** `dismissAlert` (`DELETE /alerts/{id}`) — no backend route. Remove the dismiss affordance or no-op it client-side. Note inline.

- [ ] **Step 5: Typecheck + commit**

```bash
cd frontend && npx tsc -b --noEmit
git add frontend/src/api/admin.ts frontend/src/hooks frontend/src/pages
git commit -m "[FULLSTACK] refactor: adapt campaign/creatives/KPI calls to backend"
```

### Task 13: Verify matched-path response shapes

**Files:** `frontend/src/types/admin.ts` + any page rendering a matched endpoint.

- [ ] **Step 1:** For each ✅ endpoint in the audit (campaigns CRUD, mandates CRUD, creatives, activations physical logs), open the backend `response_model` (schemas) and compare field-by-field with the frontend TS type. Fix mismatches (snake_case vs camelCase, nullable, nested shapes). Backend wins.
- [ ] **Step 2:** `cd frontend && npx tsc -b --noEmit` → no errors.
- [ ] **Step 3: Commit**

```bash
git add frontend/src/types frontend/src/pages
git commit -m "[FULLSTACK] fix: align frontend types to backend response models"
```

---

## Phase 4 — Stub external calls

### Task 14: `NTM_STUB_EXTERNAL` gate for LLM + tools + activation

**Files:**
- Create: `backend/app/external/__init__.py`, `backend/app/external/stubs.py`
- Modify: the LLM client wrapper(s) used by agents, the tool modules under `backend/app/tools/`, and the activation task entry points — to consult the gate.
- Modify: `docker-compose.yml` (set `NTM_STUB_EXTERNAL: "1"` on `ntm-api` + `ntm-agent-worker`).
- Test: `backend/tests/external/test_stubs.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/external/test_stubs.py
from backend.app.external.stubs import stub_enabled

def test_stub_enabled_reads_env(monkeypatch):
    monkeypatch.setenv("NTM_STUB_EXTERNAL", "1")
    assert stub_enabled() is True
    monkeypatch.setenv("NTM_STUB_EXTERNAL", "0")
    assert stub_enabled() is False
    monkeypatch.delenv("NTM_STUB_EXTERNAL", raising=False)
    assert stub_enabled() is False
```

- [ ] **Step 2: Run** → FAIL (create `backend/tests/external/__init__.py`).

- [ ] **Step 3: Implement the gate**

```python
# backend/app/external/stubs.py
"""Single switch for stubbing all outbound external calls (LLMs, ad platforms, media)."""
import os

def stub_enabled() -> bool:
    return os.getenv("NTM_STUB_EXTERNAL", "0").strip().lower() in {"1", "true", "yes"}
```

- [ ] **Step 4:** Wire the gate at each external boundary. For each module that calls an external API (the agents' LLM client, `backend/app/tools/*`, digital/physical activation tasks), add at the top of the call:

```python
from backend.app.external.stubs import stub_enabled
# ...
if stub_enabled():
    return <deterministic fixture matching the real return shape>
```
Identify the boundaries by Grep for `anthropic`, `openai`, `requests`, `httpx`, `googleads`, `Client(` under `backend/app/agents` and `backend/app/tools`. Each gets a fixture return that matches its real shape (reuse existing stub fixtures where the codebase already has them, e.g. `_make_stub_creative_assets` in `campaign_service.py`).

- [ ] **Step 5:** Add to compose `environment:` for `ntm-api` and `ntm-agent-worker`:

```yaml
      NTM_STUB_EXTERNAL: "1"
```

- [ ] **Step 6: Run** `docker exec ntm-api pytest backend/tests/external -v` → PASS, then rebuild: `docker compose up -d --build ntm-api ntm-agent-worker`.

- [ ] **Step 7: Verify a real task round-trips with no external calls**

```bash
docker exec ntm-api python -c "from backend.app.tasks import run_mandate_analysis; print(run_mandate_analysis.delay().id)"
docker logs ntm-agent-worker --tail 20
```
Expected: task `succeeded`, no outbound network errors.

- [ ] **Step 8: Commit**

```bash
git add backend/app/external backend/tests/external docker-compose.yml backend/app/agents backend/app/tools
git commit -m "[FULLSTACK] feat: NTM_STUB_EXTERNAL gate stubs all external calls"
```

---

## Phase 5 — End-to-end verification

### Task 15: Golden-path integration smoke test

**Files:**
- Create: `backend/tests/integration/test_full_stack_smoke.py`

- [ ] **Step 1: Write the test** — drive the ASGI app with an authed client (seed a user in the fixture DB, login, then walk the path). Follow the fixture style in `backend/tests/integration/conftest.py`.

```python
# backend/tests/integration/test_full_stack_smoke.py
import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.scripts.seed import seed_all, TENANT_ID

@pytest.mark.asyncio
async def test_login_then_list_mandates(db_session):
    await seed_all(db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as ac:
        r = await ac.post("/api/v1/auth/login", json={"email": "admin@acme.test", "password": "devpass123"})
        assert r.status_code == 200
        token = r.json()["token"]
        h = {"Authorization": f"Bearer {token}", "X-Tenant-ID": TENANT_ID}
        r2 = await ac.get("/api/v1/mandates", headers=h)
        assert r2.status_code == 200
        assert isinstance(r2.json(), list)
```
Note: this requires the test app to use the same `db_session` engine the middleware loads from. If the integration conftest overrides `get_db`/engine, ensure the middleware's `get_session_local()` is monkeypatched to the test engine in the fixture (add that override to `conftest.py`).

- [ ] **Step 2: Run** `docker exec ntm-api pytest backend/tests/integration/test_full_stack_smoke.py -v` → PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/integration/test_full_stack_smoke.py backend/tests/integration/conftest.py
git commit -m "[FULLSTACK] test: golden-path full-stack smoke"
```

### Task 16: Full suite + manual walkthrough

- [ ] **Step 1:** `docker exec ntm-api pytest -q` → all pass, coverage ≥ 60%.
- [ ] **Step 2:** `cd frontend && npm test` → all vitest suites pass (update any suite broken by Task 11–13 type/route changes).
- [ ] **Step 3:** `cd frontend && npm run dev`; open `:5173`; log in as `admin@acme.test` / `devpass123`. Walk: login → RBAC per role → onboarding → mandates (create, list, detail) → campaigns (create, detail tabs) → creative studio → analytics/KPIs → admin. Confirm data persists across reload and the network tab shows calls to `localhost:8000` (no MSW).
- [ ] **Step 4:** `git commit --allow-empty -m "[FULLSTACK] chore: full-stack verification complete"`

---

## Self-Review notes (author)
- **Spec coverage:** P0 blockers → Tasks 1–6, 8; A4 seed → Task 7; A5 Mongo env → Task 5; missing routes (P2) → Tasks 9–10 (+ register in Task 4; `/clients` onboarding is deferred — see below); P3 reconcile → Tasks 11–13; P4 stubs → Task 14; P5 verify → Tasks 15–16.
- **Deferred:** `POST /clients` (onboarding multipart) is **not** implemented as a task — onboarding can run on existing flows without it, and the spec marked it optional. If onboarding must persist a client+logo, add a task mirroring Task 9 with a MinIO upload (out of scope for first pass; flag to user).
- **Type consistency:** `current_user`/`get_current_tenant` signatures (Request-based) are used consistently by `require_role` and routers (no router signature change needed since they already `Depends(get_current_tenant)` / `Depends(require_role(...))`). `write_jwt` defined in Task 4 is used only there. Seed constants (`TENANT_ID`, `EMAIL_BY_ROLE`, `DEV_PASSWORD`) reused in Tasks 8 and 15.
- **Known assumption to verify during execution:** the test `db_session` fixture and whether integration tests override the middleware's session source (called out inline in Task 15).
