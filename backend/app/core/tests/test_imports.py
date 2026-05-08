import pytest


def test_can_import_config():
    from backend.app.core import settings
    assert settings is not None


def test_can_import_models():
    from backend.app.core import User, Role, Tenant, Base
    assert User is not None


def test_can_import_schemas():
    from backend.app.core import UserCreate, UserRead, TokenResponse
    assert UserCreate is not None


def test_can_import_auth():
    from backend.app.core import fastapi_users, current_user
    assert fastapi_users is not None


def test_can_import_exceptions():
    from backend.app.core import TenantMismatchException, InvalidTokenException
    assert TenantMismatchException is not None


def test_can_import_utilities():
    from backend.app.core import get_user_by_email, validate_user_role
    assert get_user_by_email is not None


def test_can_import_dependencies():
    from backend.app.core import get_current_tenant
    assert get_current_tenant is not None


def test_can_import_middleware():
    from backend.app.core import TenantValidationMiddleware
    assert TenantValidationMiddleware is not None
