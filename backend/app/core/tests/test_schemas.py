import pytest
from pydantic import ValidationError

from backend.app.core.schemas import RoleRead, TokenResponse, UserCreate, UserRead


def test_user_create_schema():
    """UserCreate should require email and password"""
    data = {
        "email": "newuser@example.com",
        "password": "SecurePassword123!"
    }
    user = UserCreate(**data)

    assert user.email == "newuser@example.com"
    assert user.password == "SecurePassword123!"

def test_user_create_invalid_email():
    """UserCreate should validate email format"""
    with pytest.raises(ValidationError):
        UserCreate(email="not-an-email", password="SecurePassword123!")

def test_user_create_missing_password():
    """UserCreate should require password"""
    with pytest.raises(ValidationError):
        UserCreate(email="user@example.com")

def test_user_read_schema():
    """UserRead should not include password"""
    data = {
        "id": "user-1",
        "email": "user@example.com",
        "is_active": True,
        "tenant_id": "tenant-1",
        "role": {
            "id": "role-1",
            "name": "viewer",
            "permissions": ["analytics.read"]
        }
    }
    user = UserRead(**data)

    assert user.email == "user@example.com"
    assert user.is_active is True
    assert not hasattr(user, "password")
    assert not hasattr(user, "hashed_password")

def test_token_response_schema():
    """TokenResponse should include access_token, refresh_token, token_type"""
    data = {
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "token_type": "bearer"
    }
    token = TokenResponse(**data)

    assert token.access_token == "eyJ0eXAiOiJKV1QiLCJhbGc..."
    assert token.token_type == "bearer"

def test_role_read_schema():
    """RoleRead should include id, name, permissions"""
    data = {
        "id": "role-1",
        "name": "tenant_admin",
        "permissions": ["tenant.manage", "user.manage"]
    }
    role = RoleRead(**data)

    assert role.name == "tenant_admin"
    assert "tenant.manage" in role.permissions
