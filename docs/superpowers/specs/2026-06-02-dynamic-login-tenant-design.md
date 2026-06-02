# Dynamic Login — Multi-Tenant RBAC Self-Registration

**Date:** 2026-06-02  
**Status:** Approved

## Problem

Login/register flow is hardcoded to `tenant-acme`. New tenants cannot self-register. Role is not derived from email. Frontend shows no feedback on what role/tenant the user will get.

## Email Parsing Contract

`roleprefix@tenantdomain.tld`

| Prefix | Role |
|--------|------|
| admin, platform | platform_admin |
| tenant | tenant_admin |
| brand | brand_manager |
| cmo | cmo |
| creative | creative_lead |
| campaign | campaign_manager |
| viewer | viewer |
| *(anything else)* | brand_manager |

- `tenant_slug = email.split('@')[1].split('.')[0].toLowerCase()`
- `role_name = EMAIL_ROLE_MAP[prefix] ?? 'brand_manager'`

## Architecture

### Backend — `auth_session.py`

`POST /api/v1/auth/register`:
1. Parse email → derive `role_name` + `tenant_slug`
2. UPSERT tenant: `SELECT` by slug, INSERT if missing (`name=slug, slug=slug, is_active=True`)
3. `SELECT` role by `role_name`
4. `INSERT` user with `tenant_id`, `role_id`, hashed password
5. Return `{token, user: {id, email, role, tenant_id}}`

`POST /api/v1/auth/login`: no changes needed — already looks up user by email.

### Frontend — `LoginPage.tsx`

Register form gains:
- Placeholder: `"e.g. tenant@yourcompany.com"`
- Live badge under email field: `"Role: Tenant Admin | Tenant: acme"` — visible once `@domain` is present

### Frontend — `admin.ts`

`register(email, password)` — no signature change. Backend handles all derivation.

### Mock — `mocks/handlers/auth.ts`

- Login handler: add `tenant_id` to mock user payload (derived from email domain)
- Register handler: already has role derivation; add `tenant_id` to response

## Files Changed

| File | Change |
|------|--------|
| `backend/app/routers/auth_session.py` | Parse email, UPSERT tenant, derive role |
| `frontend/src/pages/Login/LoginPage.tsx` | Live role/tenant preview badge |
| `frontend/src/mocks/handlers/auth.ts` | Add tenant_id to login + register response |

## Success Criteria

- `tenant@acme.com` registers → tenant "acme" created, role `tenant_admin`
- `admin@newco.com` registers → tenant "newco" created, role `platform_admin`
- `anything@foo.com` registers → tenant "foo" created, role `brand_manager`
- Existing tenant reused if slug already exists (no duplicate)
- Login always works for any registered user
- Frontend shows role + tenant preview live while typing email
