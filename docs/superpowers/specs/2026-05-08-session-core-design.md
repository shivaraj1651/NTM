# Session Core Design (TASK-001)

**Date:** 2026-05-08  
**Phase:** 0  
**Module:** `backend/app/core/`  
**Status:** Design Approved

---

## Executive Summary

Build a comprehensive authentication and multi-tenant context management system for NTM using FastAPI-Users extended with custom tenant validation middleware. The system enforces JWT-based auth with role-based access control, validates tenant access per request via `X-Tenant-ID` header, and provides structured error responses for all auth failures.

**Key design decision:** Approach 2 — Extended FastAPI-Users with Tenant-Aware Auth. Leverages FastAPI-Users for user management and JWT while layering custom multi-tenant validation.

---

## Architecture Overview

### Layer 1: Configuration (Static)
- Environment-driven settings (Pydantic)
- RBAC role definitions (immutable reference)
- Feature flags

### Layer 2: Data Models (PostgreSQL)
- User, Role, Tenant tables
- Junction table for multi-tenant access
- All models include `tenant_id` for data isolation

### Layer 3: Auth & JWT (FastAPI-Users)
- User registration, login, password management
- JWT token generation with tenant claims
- Active user filtering

### Layer 4: Middleware & Context
- Tenant header validation (`X-Tenant-ID`)
- Request context injection (via `contextvars` for async)
- Error response structuring

### Layer 5: Utilities & Dependencies
- Role validation functions
- Tenant lookup and access checks
- FastAPI dependency injection points

---

## Module Structure

```
backend/app/core/
├── __init__.py
├── config.py           # Pydantic Settings
├── models.py           # SQLAlchemy: User, Role, Tenant
├── schemas.py          # Pydantic: UserCreate, UserRead, Token
├── auth.py             # FastAPI-Users + JWT setup
├── middleware.py       # Tenant validation middleware
├── dependencies.py     # FastAPI Depends() functions
├── exceptions.py       # Structured auth exceptions
├── utils.py            # Role/tenant utility functions
├── security.py         # Password/token helpers
└── tests/
    ├── conftest.py     # Test fixtures
    ├── test_auth.py    # Middleware & JWT tests
    ├── test_utils.py   # Utility function tests
    └── test_models.py  # Schema & model tests
```

---

## 1. Configuration Module

**File:** `core/config.py`

Pydantic Settings class reads from `.env` at startup. Configuration includes:

### Database
- `DATABASE_URL`: PostgreSQL async connection string

### JWT Configuration
- `SECRET_KEY`: Secret for signing tokens
- `ALGORITHM`: Signing algorithm (default: HS256)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token lifetime (default: 30)
- `REFRESH_TOKEN_EXPIRE_DAYS`: Refresh token lifetime (default: 7)

### RBAC Role Definitions
```python
RBAC_ROLES = {
    "platform_admin": ["*"],  # Wildcard = all permissions
    "tenant_admin": ["tenant.manage", "user.manage", "brand.manage"],
    "brand_manager": ["brand.manage", "campaign.manage"],
    "cmo": ["campaign.manage", "analytics.read"],
    "creative_lead": ["campaign.manage", "asset.manage"],
    "campaign_manager": ["campaign.manage"],
    "viewer": ["analytics.read"]
}
```

Role definitions are immutable at runtime. All modules reference this single source of truth.

### Feature Flags
```python
FEATURE_FLAGS = {
    "enable_refresh_token_rotation": True,
    "require_2fa": False,
    "log_auth_events": True
}
```

**Design principle:** Configuration is injected as a singleton. No module reads `.env` directly.

---

## 2. Database Models

**File:** `core/models.py`

### Tenant Table
- `id` (UUID, PK)
- `name` (String, non-null)
- `is_active` (Boolean, default=True)
- `created_at` (DateTime, auto)

### Role Table
- `id` (UUID, PK)
- `name` (String, unique, non-null) — matches config key (e.g., "tenant_admin")
- `permissions` (JSON) — synced from `RBAC_ROLES` config

### User Table
- `id` (UUID, PK)
- `email` (String, unique, non-null)
- `hashed_password` (String, non-null)
- `is_active` (Boolean, default=True)
- `tenant_id` (UUID, FK → tenants.id, non-null) — **primary tenant**
- `role_id` (UUID, FK → roles.id, non-null) — one role per user
- `created_at` (DateTime, auto)

### User-Tenant Access (Junction Table)
- `user_id` (UUID, FK → user.id, PK)
- `tenant_id` (UUID, FK → tenants.id, PK)

Allows a user to access secondary tenants beyond their primary tenant.

**Invariants:**
- Every user must belong to at least one tenant (primary)
- A user can only have one role (no role inheritance)
- A user's primary tenant is always in their access list (implied by design, not enforced in DB)

---

## 3. JWT Payload Structure

When a user logs in, the issued JWT contains:

```json
{
  "sub": "user-id-uuid",
  "email": "user@example.com",
  "role": "tenant_admin",
  "primary_tenant": "tenant-uuid",
  "allowed_tenants": ["tenant-uuid", "secondary-tenant-uuid"],
  "exp": 1234567890,
  "iat": 1234567800
}
```

- `sub`, `email`, `exp`, `iat` are standard JWT claims
- `role` is the user's single role (string)
- `primary_tenant` is the user's home tenant
- `allowed_tenants` is the list of all accessible tenants (primary + secondary)

The middleware uses `allowed_tenants` to validate the `X-Tenant-ID` header.

---

## 4. Authentication Backend

**File:** `core/auth.py`

Uses FastAPI-Users with a custom JWT strategy:

```python
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import JWTStrategy

jwt_strategy = JWTStrategy(
    secret=settings.SECRET_KEY,
    lifetime_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    algorithm=settings.ALGORITHM
)

fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_db,
    [jwt_strategy],
)

current_user = fastapi_users.current_user(active=True)
```

**Responsibilities:**
- Password hashing (via `fastapi_users.password`)
- User registration/login endpoints (via `fastapi_users.router`)
- JWT encoding/decoding (via `JWTStrategy`)
- Active user filtering (via `current_user` dependency)

**What we DON'T customize here:**
- JWT signing (FastAPI-Users handles it)
- Password validation (FastAPI-Users handles it)

**What we DO customize:**
- Login endpoint to inject tenant claims into JWT (done in a custom login router override)
- Token refresh to update tenant claims if user's access changed

---

## 5. Middleware: Tenant Validation

**File:** `core/middleware.py`

### TenantValidationMiddleware

Runs **after** FastAPI-Users auth middleware. Validates `X-Tenant-ID` header and injects tenant context.

**Flow:**

1. Skip auth for public endpoints (`/docs`, `/auth/login`, `/openapi.json`)
2. Extract `X-Tenant-ID` header
   - **If missing:** Return 400 `MISSING_TENANT_HEADER`
3. Extract user from JWT (set by FastAPI-Users auth middleware in `request.state.user`)
   - **If missing:** Return 401 `UNAUTHORIZED`
4. Parse JWT claims to get `allowed_tenants`
5. Validate `tenant_id` is in `allowed_tenants`
   - **If not:** Return 403 `TENANT_MISMATCH`
6. Store `tenant_id` in:
   - `request.state.tenant_id` — for dependencies
   - `contextvars.ContextVar('tenant_id')` — for async background functions
7. Call next middleware/route

### Error Response Format

All errors follow this structure:
```json
{
  "error_code": "ERROR_CODE",
  "message": "Human-readable description",
  "timestamp": "2026-05-08T14:23:45.123456Z"
}
```

**Error codes:**
- `MISSING_TENANT_HEADER` (400)
- `UNAUTHORIZED` (401)
- `INVALID_TOKEN` (401)
- `TENANT_MISMATCH` (403)
- `TENANT_FORBIDDEN` (403)
- `INSUFFICIENT_PERMISSIONS` (403)

---

## 6. Dependencies for Routes

**File:** `core/dependencies.py`

### Primary Dependencies

```python
async def get_current_tenant() -> str:
    """Return the validated tenant_id from context"""
    return tenant_context.get()

async def get_current_user_with_tenant(
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant)
) -> tuple[User, str]:
    """Return both user and validated tenant"""
    return user, tenant_id
```

**Usage in routes:**
```python
@router.get("/brands")
async def list_brands(
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant)
):
    # Both user and tenant_id are validated by middleware
    # Query: SELECT * FROM brands WHERE tenant_id = ?
    pass
```

**Design principle:** All routes depend on `get_current_tenant()` or `current_user`. Middleware validates before dependencies run.

---

## 7. Exception Handling

**File:** `core/exceptions.py`

Custom exceptions inherit from `AuthException`, which extends FastAPI's `HTTPException`.

**Exception hierarchy:**
```
AuthException
├── InvalidTokenException(401)
├── TenantMismatchException(403)
├── MissingTenantHeaderException(400)
└── InsufficientPermissionsException(403)
```

**Usage:**
```python
if not has_access:
    raise TenantMismatchException(tenant_id)
```

FastAPI automatically converts exceptions to the structured JSON response.

---

## 8. Utility Functions

**File:** `core/utils.py`

### Tenant & User Lookups
- `get_user_by_email(session, email)` — Query user by email
- `get_user_tenants(session, user_id)` — List all tenants (primary + secondary)
- `get_tenant_by_id(session, tenant_id)` — Query active tenant
- `user_has_tenant_access(session, user_id, tenant_id)` — Boolean check

### Role & Permission Validation
- `validate_user_role(session, user_id, required_permission)` — Check if user's role has permission
- Supports wildcard permissions (platform_admin = "*")

**Design principle:** Utilities are async (SQLAlchemy async session). Called from services/routers, not from within middleware.

---

## 9. Data Flow Example

### User Login
1. POST `/auth/login` with email + password
2. FastAPI-Users validates credentials
3. Query user, load tenant + secondary tenants
4. Generate JWT with tenant claims (via custom login router)
5. Return access_token + refresh_token

### Authenticated Request
1. Client sends: `GET /brands` + `Authorization: Bearer <jwt>` + `X-Tenant-ID: tenant-123`
2. FastAPI-Users middleware decodes JWT, sets `request.state.user`
3. TenantValidationMiddleware validates:
   - `X-Tenant-ID` header present
   - tenant_id in JWT's `allowed_tenants`
   - Sets `request.state.tenant_id`
4. Route handler receives `user` and `tenant_id` via dependencies
5. Route executes query: `SELECT * FROM brands WHERE tenant_id = ?`
6. Return results (guaranteed to be from the validated tenant)

---

## 10. Testing Strategy

**Test structure:**

- **Unit tests** (`test_utils.py`): Role validation, tenant access checks
- **Integration tests** (`test_auth.py`): Middleware flow, JWT validation, error codes
- **Fixtures** (`conftest.py`): Test users, tenants, roles

**Test coverage targets:**

- Middleware:
  - ✓ Valid token + valid tenant → request proceeds
  - ✓ Missing header → 400 MISSING_TENANT_HEADER
  - ✓ Invalid token → 401 UNAUTHORIZED
  - ✓ Valid token + forbidden tenant → 403 TENANT_MISMATCH

- Utilities:
  - ✓ Role validation (wildcard, specific permission)
  - ✓ Tenant access checks (primary + secondary)
  - ✓ User lookups

- Models:
  - ✓ Unique constraints (email, role name)
  - ✓ Foreign key relationships

All tests use async SQLAlchemy test session (in-memory or test DB).

---

## 11. Security Considerations

### Tenant Isolation
- Middleware validates every request before it reaches route handlers
- No route can proceed without valid tenant context
- Database queries must include `tenant_id` filter (enforced by convention, not ORM-level)

### Password Security
- FastAPI-Users handles hashing (bcrypt or argon2)
- Passwords never transmitted in JWTs or logs

### Token Security
- JWT secret stored in `.env`, never committed
- Token expiration enforced by FastAPI-Users
- Refresh token rotation optional (via feature flag)

### Error Disclosure
- Auth errors include error codes but not internal details
- Timestamp included for debugging without exposing system internals

---

## 12. Deployment & .env Requirements

### Required .env Variables
```
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/ntm
SECRET_KEY=<generate-with-secrets.token_urlsafe(32)>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

### Optional .env Variables
```
FEATURE_FLAGS={"enable_refresh_token_rotation": true, "require_2fa": false, ...}
LOG_LEVEL=INFO
```

---

## 13. Future Extensions (Out of Scope)

- Multi-role support (currently one role per user)
- Fine-grained permission model (currently role-level)
- 2FA/MFA
- Session revocation (token blacklist)
- Audit logging of auth events
- OAuth2/SSO integrations

These are explicitly NOT part of Phase 0.

---

## Success Criteria

- ✓ All routes in NTM enforce `tenant_id` from validated JWT
- ✓ No cross-tenant data leakage (tested)
- ✓ Structured error responses for all auth failures
- ✓ Role-based access control enforced at middleware level
- ✓ Tests pass (unit + integration)
- ✓ Configuration is environment-driven

---

## Dependencies

- FastAPI 0.104+
- FastAPI-Users 12.0+
- SQLAlchemy 2.0+ (async)
- python-jose
- passlib
- pydantic-settings

---

## Related Tasks

- TASK-000: Repo initialization (✓ complete)
- TASK-001: Session core (this task)
- TASK-002: Models & schemas (depends on this)
- TASK-003+: Router implementations (depend on this)
