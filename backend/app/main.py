"""NTM FastAPI application entry point."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.audit_middleware import AuditMiddleware
from backend.app.core.auth import auth_backend, fastapi_users
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

app.add_middleware(AuditMiddleware)
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
