"""NTM Session Core - Authentication, Authorization, Multi-Tenant Context."""

# Config
# Auth
from backend.app.core.auth import current_user, fastapi_users, get_user_db
from backend.app.core.config import settings

# Dependencies
from backend.app.core.dependencies import (
    get_current_tenant,
    get_current_user_with_tenant,
    tenant_context,
)

# Exceptions
from backend.app.core.exceptions import (
    AuthException,
    InsufficientPermissionsException,
    InvalidTokenException,
    MissingTenantHeaderException,
    TenantMismatchException,
)

# Middleware
from backend.app.core.middleware import TenantValidationMiddleware

# Models
from backend.app.core.models import Base, Role, Tenant, User, user_tenant_access

# Schemas
from backend.app.core.schemas import (
    RoleRead,
    TenantRead,
    TokenResponse,
    UserCreate,
    UserRead,
    UserUpdate,
)

# Security
from backend.app.core.security import (
    InvalidTokenError,
    TokenExpiredError,
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)

# Utilities
from backend.app.core.utils import (
    get_tenant_by_id,
    get_user_by_email,
    get_user_tenants,
    user_has_tenant_access,
    validate_user_role,
)

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
