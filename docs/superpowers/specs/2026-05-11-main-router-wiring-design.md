# Design: main.py + Router Wiring

**Date:** 2026-05-11  
**Scope:** Create `backend/app/main.py` and update `backend/app/routers/__init__.py` to wire all existing routers into a runnable FastAPI application.

---

## Problem

No FastAPI app entry point exists. Three routers (`mandate.py`, `campaign.py`, `creative_director.py`) are implemented but never registered to an app instance, making the API non-runnable.

---

## Architecture

```
backend/app/
├── main.py                  ← FastAPI app, middleware, CORS, health check
└── routers/
    ├── __init__.py          ← register_routers() aggregator
    ├── mandate.py           (exists — prefix /api/v1)
    ├── campaign.py          (exists — prefix /api/v1)
    └── creative_director.py (exists — prefix /api/agents/creative-director)
```

**Request flow:**
```
Request → CORSMiddleware → TenantValidationMiddleware → Router → Agent/Service
```

`main.py` owns app config and middleware only. `routers/__init__.py` owns all `include_router` calls. This separation means adding future routers (AGT-07 to AGT-11) touches only `routers/__init__.py`.

---

## `main.py`

- Creates `FastAPI(title="NTM API", version="1.0.0")`
- Mounts `CORSMiddleware`:
  - Origins: `FRONTEND_URL` env var, fallback `http://localhost:3000`
  - Methods: `GET, POST, PUT, DELETE`
  - Headers: `Content-Type, Authorization, X-Tenant-ID`
- Mounts `TenantValidationMiddleware` (from `backend.app.core.middleware`)
- Mounts fastapi_users auth routes at `/api/v1/auth`
- Calls `register_routers(app)` from `routers/__init__.py`
- Exposes `GET /health → {"status": "ok"}`

---

## `routers/__init__.py`

Single function `register_routers(app: FastAPI) -> None` that calls `app.include_router()` for each domain router:

| Router | Prefix (already on router) |
|--------|---------------------------|
| `mandate.router` | `/api/v1` |
| `campaign.router` | `/api/v1` |
| `creative_director.router` | `/api/agents/creative-director` |

No prefix overrides — routers self-declare their prefixes. Future routers added here.

---

## CORS

Single `FRONTEND_URL` env var. If multiple origins are needed later, extend to `FRONTEND_URLS` (comma-separated). No changes to this design required for that extension.

---

## Out of Scope

- AGT-07 to AGT-11 routers (separate task)
- Auth fix for `creative_director.py` router (separate task)
- AGT-01 mandate_analyst wiring (separate task)
- Database connection pooling / lifespan events (not needed until services require shared connections)
