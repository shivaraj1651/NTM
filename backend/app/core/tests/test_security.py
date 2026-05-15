import pytest
from backend.app.core.security import hash_password, verify_password, create_access_token, decode_token
from datetime import timedelta


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
    from backend.app.core.security import TokenExpiredError
    import time

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
