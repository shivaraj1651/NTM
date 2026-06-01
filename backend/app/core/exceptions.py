"""
Custom exception classes for auth and tenant validation errors.

All exceptions inherit from FastAPI's HTTPException and provide structured
error responses with error_code, message, and timestamp for consistent
error handling across the API.
"""

from datetime import UTC, datetime

from fastapi import HTTPException


class AuthException(HTTPException):
    """
    Base auth exception with structured error response.

    Subclasses should call super().__init__() with error_code, message, and status_code.
    The detail attribute is automatically set to a structured dict.
    """
    def __init__(self, error_code: str, message: str, status_code: int = 401):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.detail = {
            "error_code": error_code,
            "message": message,
            "timestamp": datetime.now(UTC).isoformat()
        }
        super().__init__(status_code=status_code, detail=self.detail)


class InvalidTokenException(AuthException):
    """Raised when JWT token is invalid, malformed, or expired."""
    def __init__(self):
        super().__init__(
            error_code="INVALID_TOKEN",
            message="JWT token is invalid or expired",
            status_code=401
        )


class TenantMismatchException(AuthException):
    """Raised when user tries to access a tenant they don't have access to."""
    def __init__(self, tenant_id: str):
        super().__init__(
            error_code="TENANT_MISMATCH",
            message=f"User does not have access to tenant {tenant_id}",
            status_code=403
        )


class MissingTenantHeaderException(AuthException):
    """Raised when X-Tenant-ID header is missing from request."""
    def __init__(self):
        super().__init__(
            error_code="MISSING_TENANT_HEADER",
            message="X-Tenant-ID header is required",
            status_code=400
        )


class InsufficientPermissionsException(AuthException):
    """Raised when user lacks required permission for an action."""
    def __init__(self, required_permission: str):
        super().__init__(
            error_code="INSUFFICIENT_PERMISSIONS",
            message=f"User lacks required permission: {required_permission}",
            status_code=403
        )
