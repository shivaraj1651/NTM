"""
Tests for tenant validation middleware.

Verifies X-Tenant-ID header validation, tenant context injection,
and proper error handling for missing/invalid tenant headers.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from starlette.responses import JSONResponse

from backend.app.core.exceptions import (
    InvalidTokenException,
    MissingTenantHeaderException,
    TenantMismatchException,
)
from backend.app.core.middleware import TenantValidationMiddleware


def test_middleware_can_be_instantiated():
    """Middleware should instantiate correctly."""
    app = FastAPI()
    middleware = TenantValidationMiddleware(app)
    assert middleware is not None


def test_middleware_has_dispatch_method():
    """Middleware should have dispatch method."""
    app = FastAPI()
    middleware = TenantValidationMiddleware(app)
    assert hasattr(middleware, 'dispatch')
    assert callable(middleware.dispatch)


@pytest.mark.asyncio
async def test_middleware_dispatch_with_public_endpoint():
    """Middleware should skip validation for /docs endpoint."""
    # Mock request to /docs
    mock_request = MagicMock(spec=Request)
    mock_request.url.path = "/docs"
    mock_request.headers = {}

    mock_call_next = AsyncMock(return_value=JSONResponse({"message": "docs"}))

    middleware = TenantValidationMiddleware(mock_call_next)
    _response = await middleware.dispatch(mock_request, mock_call_next)

    # Should call next without validation
    assert mock_call_next.called


class _FakeSession:
    """Async context manager standing in for an AsyncSession (middleware opens one)."""
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _build_request(path="/protected", headers=None):
    """Build a fake Starlette request with an assignable state."""
    from types import SimpleNamespace
    req = MagicMock()
    req.url = SimpleNamespace(path=path)
    req.method = "GET"
    req.headers = headers or {}
    req.state = SimpleNamespace()
    return req


@pytest.mark.asyncio
async def test_middleware_dispatch_requires_tenant_header():
    """With a valid token but no X-Tenant-ID header, middleware returns 400."""
    req = _build_request(headers={"Authorization": "Bearer validtoken"})
    mock_call_next = AsyncMock()
    middleware = TenantValidationMiddleware(mock_call_next)

    with patch("backend.app.core.middleware.decode_user_id", return_value="user-1"), \
         patch("backend.app.core.middleware.get_session_local",
               return_value=lambda: _FakeSession()), \
         patch("backend.app.core.middleware.load_user_and_tenants",
               new=AsyncMock(return_value=(MagicMock(), ["tenant-123"]))):
        response = await middleware.dispatch(req, mock_call_next)

    assert response.status_code == 400
    assert not mock_call_next.called


@pytest.mark.asyncio
async def test_middleware_dispatch_requires_valid_token():
    """A protected request with no/invalid token returns 401 before tenant checks."""
    req = _build_request(headers={})  # no Authorization
    mock_call_next = AsyncMock()
    middleware = TenantValidationMiddleware(mock_call_next)

    response = await middleware.dispatch(req, mock_call_next)

    assert response.status_code == 401
    assert not mock_call_next.called


@pytest.mark.asyncio
async def test_middleware_dispatch_with_valid_tenant():
    """Valid token + matching X-Tenant-ID passes through and injects tenant/user state."""
    req = _build_request(headers={"Authorization": "Bearer validtoken", "X-Tenant-ID": "tenant-123"})
    user = MagicMock()
    mock_response = JSONResponse({"status": "ok"})
    mock_call_next = AsyncMock(return_value=mock_response)
    middleware = TenantValidationMiddleware(mock_call_next)

    with patch("backend.app.core.middleware.decode_user_id", return_value="user-1"), \
         patch("backend.app.core.middleware.get_session_local",
               return_value=lambda: _FakeSession()), \
         patch("backend.app.core.middleware.load_user_and_tenants",
               new=AsyncMock(return_value=(user, ["tenant-123"]))):
        response = await middleware.dispatch(req, mock_call_next)

    assert response == mock_response
    assert mock_call_next.called
    assert req.state.tenant_id == "tenant-123"
    assert req.state.user is user


def test_missing_tenant_exception_has_correct_status():
    """MissingTenantHeaderException should have 400 status code."""
    exc = MissingTenantHeaderException()
    assert exc.status_code == 400
    assert exc.error_code == "MISSING_TENANT_HEADER"


def test_tenant_mismatch_exception_has_correct_status():
    """TenantMismatchException should have 403 status code."""
    exc = TenantMismatchException("tenant-456")
    assert exc.status_code == 403
    assert exc.error_code == "TENANT_MISMATCH"


def test_invalid_token_exception_has_correct_status():
    """InvalidTokenException should have 401 status code."""
    exc = InvalidTokenException()
    assert exc.status_code == 401
    assert exc.error_code == "INVALID_TOKEN"


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


# ── CORS and app structure ────────────────────────────────────────────────────

def test_main_app_has_cors_middleware():
    from backend.app.main import app
    # Starlette stores middleware as Middleware(cls=...) objects
    cls_names = [getattr(m, "cls", type(m)).__name__ for m in app.user_middleware]
    cors_present = any("CORS" in n or "cors" in n.lower() for n in cls_names)
    assert cors_present, f"CORS middleware not found. Classes: {cls_names}"


def test_app_includes_campaign_routes():
    """Campaign routes should be registered in main app."""
    from backend.app.main import app
    paths = {getattr(r, "path", "") for r in app.routes}
    assert any("/campaigns" in p for p in paths), \
        f"No campaign routes found. Paths: {sorted(p for p in paths if p)}"
