"""Endpoint tests for admin router — tenant, user, and audit-log management."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.routers.admin import router, require_platform_admin
from backend.app.core.auth import current_user
from backend.app.core.dependencies import get_current_tenant
from backend.app.core.models import User
from backend.app.db import get_async_session


def make_admin_user():
    role = MagicMock()
    role.name = "platform_admin"
    user = MagicMock(spec=User)
    user.id = "admin-user-id"
    user.email = "admin@ntm.io"
    user.is_active = True
    user.role = role
    return user


def make_non_admin_user():
    role = MagicMock()
    role.name = "viewer"
    user = MagicMock(spec=User)
    user.id = "viewer-user-id"
    user.email = "viewer@ntm.io"
    user.is_active = True
    user.role = role
    return user


def make_app(admin: bool = True):
    app = FastAPI()
    app.include_router(router)
    mock_user = make_admin_user() if admin else make_non_admin_user()
    mock_db = AsyncMock()
    app.dependency_overrides[current_user] = lambda: mock_user
    app.dependency_overrides[get_current_tenant] = lambda: "test-tenant"
    app.dependency_overrides[get_async_session] = lambda: mock_db
    if admin:
        app.dependency_overrides[require_platform_admin] = lambda: mock_user
    return app, mock_db


# ── POST /api/v1/admin/tenants ────────────────────────────────────────────────

def test_create_tenant():
    app, mock_db = make_app()
    mock_tenant = MagicMock()
    mock_tenant.id = "tenant-001"
    mock_tenant.name = "Acme Corp"
    mock_tenant.slug = "acme-corp"
    mock_tenant.is_active = True

    with patch("backend.app.routers.admin.AsyncSession") as _:
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, "id", "tenant-001"))

        client = TestClient(app)
        response = client.post(
            "/api/v1/admin/tenants",
            json={"name": "Acme Corp", "slug": "acme-corp"},
        )

    assert response.status_code in (200, 201)


# ── GET /api/v1/admin/tenants ─────────────────────────────────────────────────

def test_list_tenants():
    app, mock_db = make_app()

    mock_result = MagicMock()
    mock_tenant = MagicMock()
    mock_tenant.id = "tenant-001"
    mock_tenant.name = "Acme Corp"
    mock_tenant.slug = "acme-corp"
    mock_tenant.is_active = True
    mock_result.scalars.return_value.all.return_value = [mock_tenant]
    mock_db.execute = AsyncMock(return_value=mock_result)

    client = TestClient(app)
    response = client.get("/api/v1/admin/tenants")

    assert response.status_code == 200
    body = response.json()
    assert "tenants" in body
    assert len(body["tenants"]) == 1


# ── POST /api/v1/admin/users ──────────────────────────────────────────────────

def test_create_user():
    app, mock_db = make_app()

    mock_role_result = MagicMock()
    mock_role = MagicMock()
    mock_role.id = "role-001"
    mock_role_result.scalar_one_or_none.return_value = mock_role
    mock_db.execute = AsyncMock(return_value=mock_role_result)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    client = TestClient(app)
    response = client.post(
        "/api/v1/admin/users",
        json={
            "email": "newuser@ntm.io",
            "full_name": "New User",
            "password": "secure-pass-123",
            "role_name": "viewer",
            "tenant_id": "test-tenant",
        },
    )

    assert response.status_code in (200, 201)


# ── PUT /api/v1/admin/users/{user_id}/role ────────────────────────────────────

def test_update_user_role():
    app, mock_db = make_app()

    mock_result = MagicMock()
    mock_result.rowcount = 1
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.commit = AsyncMock()

    client = TestClient(app)
    response = client.put(
        "/api/v1/admin/users/user-001/role",
        json={"role_id": "role-002"},
    )

    assert response.status_code == 200


# ── GET /api/v1/admin/audit-log ───────────────────────────────────────────────

def test_audit_log():
    app, mock_db = make_app()

    mock_result = MagicMock()
    mock_log = MagicMock()
    mock_log.id = "log-001"
    mock_log.entity_type = "mandate"
    mock_log.entity_id = "mand-001"
    mock_log.action = "approved"
    mock_log.actor_user_id = "admin-user-id"
    mock_log.timestamp = MagicMock()
    mock_log.timestamp.isoformat.return_value = "2026-05-21T00:00:00Z"
    mock_log.comment = "Looks good"
    mock_log.ip_address = "127.0.0.1"
    mock_log.version = 1
    mock_result.scalars.return_value.all.return_value = [mock_log]
    mock_db.execute = AsyncMock(return_value=mock_result)

    client = TestClient(app)
    response = client.get("/api/v1/admin/audit-log?tenant_id=test-tenant")

    assert response.status_code == 200
    body = response.json()
    assert "logs" in body


# ── Non-admin access should be forbidden ─────────────────────────────────────

def test_non_admin_cannot_create_tenant():
    app = FastAPI()
    app.include_router(router)
    mock_user = make_non_admin_user()
    mock_db = AsyncMock()
    app.dependency_overrides[current_user] = lambda: mock_user
    app.dependency_overrides[get_current_tenant] = lambda: "test-tenant"
    app.dependency_overrides[get_async_session] = lambda: mock_db

    client = TestClient(app)
    response = client.post(
        "/api/v1/admin/tenants",
        json={"name": "Unauthorized Corp", "slug": "unauthorized"},
    )

    assert response.status_code == 403
