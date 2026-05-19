"""
Tests for tenant validation middleware.

Verifies X-Tenant-ID header validation, tenant context injection,
and proper error handling for missing/invalid tenant headers.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI, Request
from starlette.responses import JSONResponse
from backend.app.core.middleware import TenantValidationMiddleware
from backend.app.core.exceptions import (
    MissingTenantHeaderException,
    TenantMismatchException,
    InvalidTokenException
)
from backend.app.core.dependencies import tenant_context




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
    response = await middleware.dispatch(mock_request, mock_call_next)

    # Should call next without validation
    assert mock_call_next.called


@pytest.mark.asyncio
async def test_middleware_dispatch_requires_tenant_header():
    """Middleware should raise exception for protected endpoint without tenant header."""
    mock_request = MagicMock(spec=Request)
    mock_request.url.path = "/protected"
    mock_request.headers = {}

    mock_call_next = AsyncMock()

    middleware = TenantValidationMiddleware(mock_call_next)
    response = await middleware.dispatch(mock_request, mock_call_next)

    # Should return 400 for missing tenant header
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_middleware_dispatch_with_valid_tenant():
    """Middleware should inject tenant_id for valid request."""
    # Create a simple state class that allows attribute assignment
    class StateObj:
        pass

    mock_request = MagicMock()
    mock_request.url.path = "/protected"
    mock_request.headers = {"X-Tenant-ID": "tenant-123"}

    # Create a real state object that supports attribute assignment
    state = StateObj()
    state.user = MagicMock()
    state.allowed_tenants = ["tenant-123"]
    mock_request.state = state

    mock_response = JSONResponse({"status": "ok"})
    mock_call_next = AsyncMock(return_value=mock_response)

    middleware = TenantValidationMiddleware(mock_call_next)
    response = await middleware.dispatch(mock_request, mock_call_next)

    # Should pass through successfully
    assert response == mock_response
    assert mock_call_next.called
    assert mock_request.state.tenant_id == "tenant-123"


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
