from datetime import timedelta

import pytest

from backend.app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)

# ── JWT strategy and auth backend ────────────────────────────────────────────

def test_jwt_strategy_lifetime_is_positive(isolated_settings):
    from backend.app.core.auth import get_jwt_strategy
    strategy = get_jwt_strategy()
    assert strategy.lifetime_seconds > 0


def test_jwt_strategy_uses_configured_algorithm(isolated_settings):
    from backend.app.core.auth import get_jwt_strategy
    strategy = get_jwt_strategy()
    assert strategy.algorithm in ("HS256", "HS384", "HS512", "RS256", "RS384", "RS512")


def test_bearer_transport_token_url_contains_login():
    from backend.app.core.auth import bearer_transport
    # OAuth2PasswordBearer stores tokenUrl in scheme.model.flows.password.tokenUrl
    url = bearer_transport.scheme.model.flows.password.tokenUrl
    assert "login" in url


def test_auth_backend_name_is_jwt():
    from backend.app.core.auth import auth_backend
    assert auth_backend.name == "jwt"


def test_security_module_importable():
    import backend.app.core.security  # noqa: F401


def test_security_exposes_hash_and_verify():
    from backend.app.core import security
    assert hasattr(security, "hash_password") or hasattr(security, "get_password_hash")
    assert hasattr(security, "verify_password")


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch):
    """Reset the Settings singleton and inject required env vars for each test."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://localhost/test_db")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-jwt-signing-32x")
    import backend.app.core.config as cfg
    cfg._settings_instance = None
    yield
    cfg._settings_instance = None


def test_hash_password():
    """hash_password should return a bcrypt hash"""
    password = "SecurePassword123!"
    hashed = hash_password(password)

    assert hashed != password
    assert len(hashed) > 20

def test_verify_password_correct():
    """verify_password should return True for correct password"""
    password = "SecurePassword123!"
    hashed = hash_password(password)

    assert verify_password(password, hashed) == True

def test_verify_password_incorrect():
    """verify_password should return False for incorrect password"""
    password = "SecurePassword123!"
    hashed = hash_password(password)

    assert verify_password("WrongPassword", hashed) == False

def test_create_access_token():
    """create_access_token should return a valid JWT"""
    data = {
        "sub": "user-123",
        "email": "user@example.com",
        "role": "viewer",
        "allowed_tenants": ["tenant-1"]
    }
    token = create_access_token(data)

    assert isinstance(token, str)
    assert len(token) > 50
    assert "." in token

def test_decode_token_valid():
    """decode_token should return claims from a valid token"""
    data = {
        "sub": "user-123",
        "email": "user@example.com",
        "role": "viewer",
        "allowed_tenants": ["tenant-1", "tenant-2"]
    }
    token = create_access_token(data)
    decoded = decode_token(token)

    assert decoded["sub"] == "user-123"
    assert decoded["email"] == "user@example.com"
    assert "tenant-1" in decoded["allowed_tenants"]

def test_decode_token_expired():
    """decode_token should raise exception for expired token"""
    import time

    from backend.app.core.security import TokenExpiredError

    data = {"sub": "user-123"}
    token = create_access_token(data, expires_delta=timedelta(seconds=-1))
    time.sleep(0.1)

    with pytest.raises(TokenExpiredError):
        decode_token(token)

def test_decode_token_invalid():
    """decode_token should raise exception for invalid token"""
    from backend.app.core.security import InvalidTokenError

    with pytest.raises(InvalidTokenError):
        decode_token("not.a.valid.token")
