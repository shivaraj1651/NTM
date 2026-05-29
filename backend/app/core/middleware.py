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
