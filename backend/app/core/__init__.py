"""NTM Session Core - Authentication, Authorization, Multi-Tenant Context."""

# Config
from backend.app.core.config import settings

# Models
from backend.app.core.models import Base, User, Role, Tenant, user_tenant_access

# Schemas
from backend.app.core.schemas import (
    UserCreate, UserRead, UserUpdate, TokenResponse, RoleRead, TenantRead
)

# Auth
from backend.app.core.auth import fastapi_users, current_user, get_user_db

# Security
from backend.app.core.security import (
    hash_password, verify_password, create_access_token, decode_token,
    TokenExpiredError, InvalidTokenError
)

# Exceptions
from backend.app.core.exceptions import (
    AuthException, InvalidTokenException, TenantMismatchException,
    MissingTenantHeaderException, InsufficientPermissionsException
)

# Utilities
from backend.app.core.utils import (
    get_user_by_email, get_user_tenants, validate_user_role,
    get_tenant_by_id, user_has_tenant_access
)

# Dependencies
from backend.app.core.dependencies import (
    get_current_tenant, get_current_user_with_tenant, tenant_context
)

# Middleware
from backend.app.core.middleware import TenantValidationMiddleware

__all__ = [
    "settings", "Base", "User", "Role", "Tenant", "user_tenant_access",
    "UserCreate", "UserRead", "UserUpdate", "TokenResponse", "RoleRead", "TenantRead",
    "fastapi_users", "current_user", "get_user_db",
    "hash_password", "verify_password", "create_access_token", "decode_token",
    "TokenExpiredError", "InvalidTokenError",
    "AuthException", "InvalidTokenException", "TenantMismatchException",
    "MissingTenantHeaderException", "InsufficientPermissionsException",
    "get_user_by_email", "get_user_tenants", "validate_user_role",
    "get_tenant_by_id", "user_has_tenant_access",
    "get_current_tenant", "get_current_user_with_tenant", "tenant_context",
    "TenantValidationMiddleware",
]
