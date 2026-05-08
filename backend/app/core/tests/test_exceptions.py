import pytest
from fastapi import HTTPException
from backend.app.core.exceptions import (
    AuthException,
    InvalidTokenException,
    TenantMismatchException,
    MissingTenantHeaderException,
    InsufficientPermissionsException
)

def test_auth_exception_structure():
    """AuthException should create structured error response"""
    exc = AuthException(
        error_code="TEST_ERROR",
        message="Test message",
        status_code=401
    )

    assert exc.status_code == 401
    assert exc.detail["error_code"] == "TEST_ERROR"
    assert exc.detail["message"] == "Test message"
    assert "timestamp" in exc.detail

def test_invalid_token_exception():
    """InvalidTokenException should return 401 INVALID_TOKEN"""
    exc = InvalidTokenException()

    assert exc.status_code == 401
    assert exc.detail["error_code"] == "INVALID_TOKEN"
    assert "invalid or expired" in exc.detail["message"].lower()

def test_tenant_mismatch_exception():
    """TenantMismatchException should return 403 TENANT_MISMATCH"""
    exc = TenantMismatchException("tenant-xyz")

    assert exc.status_code == 403
    assert exc.detail["error_code"] == "TENANT_MISMATCH"
    assert "tenant-xyz" in exc.detail["message"]

def test_missing_tenant_header_exception():
    """MissingTenantHeaderException should return 400 MISSING_TENANT_HEADER"""
    exc = MissingTenantHeaderException()

    assert exc.status_code == 400
    assert exc.detail["error_code"] == "MISSING_TENANT_HEADER"
    assert "required" in exc.detail["message"].lower()

def test_insufficient_permissions_exception():
    """InsufficientPermissionsException should return 403 INSUFFICIENT_PERMISSIONS"""
    exc = InsufficientPermissionsException("tenant.manage")

    assert exc.status_code == 403
    assert exc.detail["error_code"] == "INSUFFICIENT_PERMISSIONS"
    assert "tenant.manage" in exc.detail["message"]

def test_auth_exception_is_http_exception():
    """AuthException should be compatible with FastAPI HTTPException"""
    exc = AuthException("TEST", "msg", 401)
    assert isinstance(exc, HTTPException)
