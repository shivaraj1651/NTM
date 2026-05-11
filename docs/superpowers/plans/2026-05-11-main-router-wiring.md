# main.py + Router Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create `backend/app/main.py` and `backend/app/routers/__init__.py` to make the NTM FastAPI application runnable with all three existing routers registered.

**Architecture:** A `register_routers()` aggregator in `routers/__init__.py` mounts all domain routers. `main.py` owns CORS, `TenantValidationMiddleware`, fastapi_users JWT auth routes, and the health check. `middleware.py` gains `/health` in its public-endpoints skip list so the health check doesn't require auth headers.

**Tech Stack:** FastAPI, Starlette CORSMiddleware, fastapi-users, pytest, starlette TestClient

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `backend/app/core/middleware.py` | Add `/health` to public endpoints skip list |
| Create | `backend/app/routers/__init__.py` | `register_routers(app)` — mounts all domain routers |
| Create | `backend/app/main.py` | FastAPI app, CORS, middleware, auth routes, health check |
| Create | `backend/tests/routers/__init__.py` | Test package marker |
| Create | `backend/tests/routers/test_router_registration.py` | Tests for `register_routers()` |
| Create | `backend/tests/test_main.py` | Tests for health check, CORS, route registration |

---

### Task 1: Add `/health` to middleware public endpoints

**Files:**
- Modify: `backend/app/core/middleware.py:19`
- Modify: `backend/app/core/tests/test_middleware.py` (append test)

- [ ] **Step 1: Write the failing test**

Append to `backend/app/core/tests/test_middleware.py`:

```python
def test_health_endpoint_skips_tenant_validation():
    """Middleware must not block /health — no tenant header required."""
    from starlette.testclient import TestClient

    app = FastAPI()
    app.add_middleware(TenantValidationMiddleware)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/health")
    assert response.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

```
cd backend
python -m pytest app/core/tests/test_middleware.py::test_health_endpoint_skips_tenant_validation -v
```

Expected: FAIL — middleware raises `InvalidTokenException` before reaching the route.

- [ ] **Step 3: Add `/health` to public endpoints**

In `backend/app/core/middleware.py`, line 19, change:

```python
        public_endpoints = ["/docs", "/openapi.json", "/redoc", "/auth/login", "/auth/register"]
```

to:

```python
        public_endpoints = ["/docs", "/openapi.json", "/redoc", "/auth/login", "/auth/register", "/health"]
```

- [ ] **Step 4: Run test to verify it passes**

```
python -m pytest app/core/tests/test_middleware.py::test_health_endpoint_skips_tenant_validation -v
```

Expected: PASS

- [ ] **Step 5: Run full suite to check for regressions**

```
python -m pytest tests/ app/core/tests/ -q
```

Expected: all previously passing tests still pass.

- [ ] **Step 6: Commit**

```
git add backend/app/core/middleware.py backend/app/core/tests/test_middleware.py
git commit -m "[TASK-017] fix: add /health to TenantValidationMiddleware public endpoints"
```

---

### Task 2: Create `routers/__init__.py`

**Files:**
- Create: `backend/app/routers/__init__.py`
- Create: `backend/tests/routers/__init__.py`
- Create: `backend/tests/routers/test_router_registration.py`

- [ ] **Step 1: Create test package marker**

Create an empty file `backend/tests/routers/__init__.py`.

- [ ] **Step 2: Write the failing tests**

Create `backend/tests/routers/test_router_registration.py`:

```python
"""Tests for routers/__init__.py register_routers()."""

import pytest
from fastapi import FastAPI


def test_register_routers_adds_mandate_routes():
    from backend.app.routers import register_routers
    app = FastAPI()
    register_routers(app)
    paths = {route.path for route in app.routes}
    assert "/api/v1/mandates/{mandate_id}/analyze-competitors" in paths
    assert "/api/v1/jobs/{job_id}" in paths


def test_register_routers_adds_campaign_routes():
    from backend.app.routers import register_routers
    app = FastAPI()
    register_routers(app)
    paths = {route.path for route in app.routes}
    assert "/api/v1/campaigns" in paths
    assert "/api/v1/campaigns/{campaign_id}" in paths
    assert "/api/v1/campaigns/{campaign_id}/confirm" in paths
    assert "/api/v1/campaigns/{campaign_id}/activation-plan" in paths
    assert "/api/v1/campaigns/{campaign_id}/approve-budget" in paths
    assert "/api/v1/campaigns/{campaign_id}/confirm-budget" in paths


def test_register_routers_adds_creative_director_routes():
    from backend.app.routers import register_routers
    app = FastAPI()
    register_routers(app)
    paths = {route.path for route in app.routes}
    assert "/api/agents/creative-director/generate" in paths
    assert "/api/agents/creative-director/health" in paths
```

- [ ] **Step 3: Run tests to verify they fail**

```
cd backend
python -m pytest tests/routers/test_router_registration.py -v
```

Expected: FAIL — `ImportError: cannot import name 'register_routers' from 'backend.app.routers'`

- [ ] **Step 4: Implement `routers/__init__.py`**

Create `backend/app/routers/__init__.py`:

```python
"""Router aggregator — mounts all domain routers onto the FastAPI app."""

from fastapi import FastAPI

from backend.app.routers.mandate import router as mandate_router
from backend.app.routers.campaign import router as campaign_router
from backend.app.routers.creative_director import router as creative_director_router


def register_routers(app: FastAPI) -> None:
    app.include_router(mandate_router)
    app.include_router(campaign_router)
    app.include_router(creative_director_router)
```

- [ ] **Step 5: Run tests to verify they pass**

```
python -m pytest tests/routers/test_router_registration.py -v
```

Expected: all 3 tests PASS

- [ ] **Step 6: Commit**

```
git add backend/app/routers/__init__.py backend/tests/routers/__init__.py backend/tests/routers/test_router_registration.py
git commit -m "[TASK-017] feat: add register_routers() aggregator to routers/__init__.py"
```

---

### Task 3: Create `main.py`

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/tests/test_main.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_main.py`:

```python
"""Tests for backend/app/main.py."""

import pytest
from starlette.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("SECRET_KEY", "testsecretkey_at_least_32_chars_long!!")
    # Re-import after env vars are set
    import importlib
    import backend.app.main as main_module
    importlib.reload(main_module)
    return TestClient(main_module.app, raise_server_exceptions=False)


def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_health_returns_status_ok(client):
    response = client.get("/health")
    assert response.json() == {"status": "ok"}


def test_cors_header_present_for_allowed_origin(client, monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:3000")
    response = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert "access-control-allow-origin" in response.headers


def test_mandate_route_registered(client):
    paths = {route.path for route in client.app.routes}
    assert "/api/v1/mandates/{mandate_id}/analyze-competitors" in paths


def test_campaign_route_registered(client):
    paths = {route.path for route in client.app.routes}
    assert "/api/v1/campaigns" in paths


def test_creative_director_route_registered(client):
    paths = {route.path for route in client.app.routes}
    assert "/api/agents/creative-director/generate" in paths


def test_auth_login_route_registered(client):
    paths = {route.path for route in client.app.routes}
    assert "/api/v1/auth/jwt/login" in paths
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd backend
python -m pytest tests/test_main.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'backend.app.main'`

- [ ] **Step 3: Implement `main.py`**

Create `backend/app/main.py`:

```python
"""NTM FastAPI application entry point."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.auth import fastapi_users, auth_backend
from backend.app.core.middleware import TenantValidationMiddleware
from backend.app.routers import register_routers

app = FastAPI(title="NTM API", version="1.0.0")

# CORS — reads FRONTEND_URL from env, falls back to localhost:3000 for dev
_frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_frontend_url],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-Tenant-ID"],
)

app.add_middleware(TenantValidationMiddleware)

# JWT auth routes: POST /api/v1/auth/jwt/login, POST /api/v1/auth/jwt/logout
app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/api/v1/auth/jwt",
    tags=["auth"],
)

register_routers(app)


@app.get("/health", tags=["ops"])
async def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 4: Run tests to verify they pass**

```
python -m pytest tests/test_main.py -v
```

Expected: all 7 tests PASS

- [ ] **Step 5: Run full suite**

```
python -m pytest tests/ app/core/tests/ -q
```

Expected: all tests pass.

- [ ] **Step 6: Verify the app starts**

```
uvicorn backend.app.main:app --reload --port 8000
```

Expected: server starts, `GET http://localhost:8000/health` returns `{"status": "ok"}`, `GET http://localhost:8000/docs` shows all 14 routes in Swagger UI.

- [ ] **Step 7: Commit**

```
git add backend/app/main.py backend/tests/test_main.py
git commit -m "[TASK-017] feat: create main.py FastAPI entry point with CORS, middleware, auth, and all routers"
```

---

## Routes exposed after completion

```
GET  /health
POST /api/v1/auth/jwt/login
POST /api/v1/auth/jwt/logout
POST /api/v1/mandates/{mandate_id}/analyze-competitors
GET  /api/v1/jobs/{job_id}
POST /api/v1/campaigns
GET  /api/v1/campaigns/{campaign_id}
PUT  /api/v1/campaigns/{campaign_id}
POST /api/v1/campaigns/{campaign_id}/confirm
GET  /api/v1/campaigns/{campaign_id}/activation-plan
POST /api/v1/campaigns/{campaign_id}/approve-budget
POST /api/v1/campaigns/{campaign_id}/confirm-budget
POST /api/agents/creative-director/generate
GET  /api/agents/creative-director/health
```
