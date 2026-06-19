"""Tests for auth_ext router — password reset flow."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.db import get_db
from backend.app.routers.auth_ext import _otp_store, router


def make_app():
    app = FastAPI()
    app.include_router(router)
    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    return app, mock_db


def _make_user(email="user@test.com"):
    user = MagicMock()
    user.id = "user-001"
    user.email = email
    user.hashed_password = "old-hash"
    return user


def _make_db_with_user(user):
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    db.execute = AsyncMock(return_value=result)
    db.commit = AsyncMock()
    return db


def _make_db_no_user():
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)
    return db


# ── POST /api/v1/auth/password-reset/request ─────────────────────────────────

def test_password_reset_request_unknown_email():
    """Returns 200 even for unknown email to avoid enumeration."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: _make_db_no_user()

    client = TestClient(app)
    response = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "nobody@example.com"},
    )

    assert response.status_code == 200
    assert "OTP" in response.json()["message"]


def test_password_reset_request_known_email():
    """Stores OTP when user exists."""
    user = _make_user("known@test.com")
    _otp_store.clear()

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: _make_db_with_user(user)

    client = TestClient(app)
    response = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "known@test.com"},
    )

    assert response.status_code == 200
    assert "known@test.com" in _otp_store
    _otp_store.clear()


# ── POST /api/v1/auth/password-reset/confirm ─────────────────────────────────

def test_password_reset_confirm_no_otp():
    """400 when no OTP has been requested."""
    _otp_store.clear()
    app, db = make_app()
    client = TestClient(app)

    response = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"email": "user@test.com", "otp": "123456", "new_password": "NewPass123!"},
    )

    assert response.status_code == 400
    assert "Invalid or expired" in response.json()["detail"]


def test_password_reset_confirm_expired_otp():
    """400 when OTP is expired."""
    email = "exp@test.com"
    _otp_store[email] = {
        "otp": "999999",
        "expires_at": datetime.now(UTC) - timedelta(minutes=1),
        "user_id": "u-1",
    }

    app, db = make_app()
    client = TestClient(app)

    response = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"email": email, "otp": "999999", "new_password": "NewPass123!"},
    )

    assert response.status_code == 400
    assert "expired" in response.json()["detail"].lower()
    _otp_store.clear()


def test_password_reset_confirm_wrong_otp():
    """400 when OTP doesn't match."""
    email = "wrong@test.com"
    _otp_store[email] = {
        "otp": "111111",
        "expires_at": datetime.now(UTC) + timedelta(minutes=9),
        "user_id": "u-1",
    }

    app, db = make_app()
    client = TestClient(app)

    response = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"email": email, "otp": "222222", "new_password": "NewPass123!"},
    )

    assert response.status_code == 400
    assert "Invalid OTP" in response.json()["detail"]
    _otp_store.clear()


def test_password_reset_confirm_success():
    """200 when OTP is valid and user exists."""
    from unittest.mock import patch as _patch

    email = "success@test.com"
    _otp_store[email] = {
        "otp": "777777",
        "expires_at": datetime.now(UTC) + timedelta(minutes=9),
        "user_id": "u-1",
    }

    user = _make_user(email)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: _make_db_with_user(user)

    with _patch("backend.app.routers.auth_ext._pwd_ctx") as mock_ctx:
        mock_ctx.hash.return_value = "hashed-new-password"
        client = TestClient(app)
        response = client.post(
            "/api/v1/auth/password-reset/confirm",
            json={"email": email, "otp": "777777", "new_password": "NewSecure@123"},
        )

    assert response.status_code == 200
    assert "updated" in response.json()["message"].lower()
    assert email not in _otp_store
    _otp_store.clear()


def test_password_reset_confirm_user_vanished():
    """404 when OTP is valid but user no longer in DB."""
    email = "gone@test.com"
    _otp_store[email] = {
        "otp": "888888",
        "expires_at": datetime.now(UTC) + timedelta(minutes=9),
        "user_id": "u-gone",
    }

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: _make_db_no_user()

    client = TestClient(app)
    response = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"email": email, "otp": "888888", "new_password": "AnyPass@1"},
    )

    assert response.status_code == 404
    _otp_store.clear()
