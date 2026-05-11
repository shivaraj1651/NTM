"""Tenant validation middleware for multi-tenant request handling."""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from backend.app.core.dependencies import tenant_context
from backend.app.core.exceptions import (
    MissingTenantHeaderException,
    TenantMismatchException,
    InvalidTokenException
)


class TenantValidationMiddleware(BaseHTTPMiddleware):
    """Validates X-Tenant-ID header and injects tenant context."""

    async def dispatch(self, request: Request, call_next):
        """Process request and validate tenant before passing to route handler."""
        # Skip auth for public endpoints
        public_endpoints = ["/docs", "/openapi.json", "/redoc", "/auth/login", "/auth/register", "/health"]
        if request.url.path in public_endpoints:
            return await call_next(request)

        try:
            # Extract X-Tenant-ID header
            tenant_id = request.headers.get("X-Tenant-ID")
            if not tenant_id:
                raise MissingTenantHeaderException()

            # Extract user from request state (set by FastAPI-Users middleware)
            user = request.state.__dict__.get("user")
            if not user:
                raise InvalidTokenException()

            # Extract allowed_tenants from request state (set by auth middleware)
            allowed_tenants = request.state.__dict__.get("allowed_tenants", [])

            # Validate tenant_id is in allowed tenants
            if tenant_id not in allowed_tenants:
                raise TenantMismatchException(tenant_id)

            # Store tenant in context for dependency injection
            tenant_context.set(tenant_id)
            request.state.tenant_id = tenant_id

            return await call_next(request)

        except Exception as exc:
            # Handle custom exceptions with status_code and detail
            if hasattr(exc, 'status_code') and hasattr(exc, 'detail'):
                return JSONResponse(
                    status_code=exc.status_code,
                    content=exc.detail
                )
            # Re-raise unexpected exceptions
            raise
