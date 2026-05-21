"""Endpoint tests for admin router — tenant, user, and audit-log management."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.routers.admin import router, require_platform_admin
from backend.app.core.auth import current_user
from backend.app.core.dependencies import get_current_tenant
from backend.app.core.models import User
from backend.app.db import get_db

_TS = datetime(2026, 5, 21, tzinfo=timezone.utc)


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
    app.dependency_overrides[get_db] = lambda: mock_db
    if admin:
        app.dependency_overrides[require_platform_admin] = lambda: mock_user
    return app, mock_db


# ── POST /api/v1/admin/tenants ────────────────────────────────────────────────

def test_create_tenant():
    app, mock_db = make_app()

    def _refresh(obj):
        obj.id = "tenant-001"
        obj.name = "Acme Corp"
        obj.is_active = True
        obj.created_at = _TS

    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock(side_effect=_refresh)

    client = TestClient(app)
    response = client.post("/api/v1/admin/tenants", json={"name": "Acme Corp"})

    assert response.status_code in (200, 201)
    body = response.json()
    assert body["name"] == "Acme Corp"


# ── GET /api/v1/admin/tenants ─────────────────────────────────────────────────

def test_list_tenants():
    app, mock_db = make_app()

    mock_tenant = MagicMock()
    mock_tenant.id = "tenant-001"
    mock_tenant.name = "Acme Corp"
    mock_tenant.is_active = True
    mock_tenant.created_at = _TS

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_tenant]
    mock_db.execute = AsyncMock(return_value=mock_result)

    client = TestClient(app)
    response = client.get("/api/v1/admin/tenants")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 1
    assert body[0]["name"] == "Acme Corp"


# ── POST /api/v1/admin/users ──────────────────────────────────────────────────

def test_create_user():
    app, mock_db = make_app()

    mock_role = MagicMock()
    mock_role.id = "role-001"

    role_result = MagicMock()
    role_result.scalar_one_or_none.return_value = mock_role

    tenant_result = MagicMock()
    tenant_result.scalar_one_or_none.return_value = MagicMock()

    mock_db.execute = AsyncMock(side_effect=[role_result, tenant_result])
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    def _refresh(obj):
        obj.id = "user-001"
        obj.email = "newuser@ntm.io"
        obj.tenant_id = "test-tenant"
        obj.is_active = True
        obj.created_at = _TS

    mock_db.refresh = AsyncMock(side_effect=_refresh)

    with patch("passlib.context.CryptContext") as MockCtx:
        MockCtx.return_value.hash.return_value = "hashed-password"
        client = TestClient(app)
        response = client.post(
            "/api/v1/admin/users",
            json={
                "email": "newuser@ntm.io",
                "password": "Secure-Pass-123",
                "role_name": "viewer",
                "tenant_id": "test-tenant",
            },
        )

    assert response.status_code in (200, 201)


# ── PUT /api/v1/admin/users/{user_id}/role ────────────────────────────────────

def test_update_user_role():
    app, mock_db = make_app()

    mock_role = MagicMock()
    mock_role.id = "role-002"
    role_result = MagicMock()
    role_result.scalar_one_or_none.return_value = mock_role

    mock_target = MagicMock()
    mock_target.id = "user-001"
    mock_target.email = "user@ntm.io"
    mock_target.tenant_id = "test-tenant"
    mock_target.is_active = True
    mock_target.created_at = _TS
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = mock_target

    mock_update_result = MagicMock()
    mock_db.execute = AsyncMock(side_effect=[role_result, user_result, mock_update_result])
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    client = TestClient(app)
    response = client.put(
        "/api/v1/admin/users/user-001/role",
        json={"role_name": "editor"},
    )

    assert response.status_code == 200


# ── GET /api/v1/admin/audit-log ───────────────────────────────────────────────

def test_audit_log():
    app, mock_db = make_app()

    mock_log = MagicMock()
    mock_log.id = "log-001"
    mock_log.tenant_id = "test-tenant"
    mock_log.entity_type = "mandate"
    mock_log.entity_id = "mand-001"
    mock_log.action = "approved"
    mock_log.actor_id = "admin-user-id"
    mock_log.notes = None
    mock_log.status_before = None
    mock_log.status_after = None
    mock_log.created_at = _TS

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_log]
    mock_db.execute = AsyncMock(return_value=mock_result)

    client = TestClient(app)
    response = client.get("/api/v1/admin/audit-log?tenant_id=test-tenant")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 1
    assert body[0]["action"] == "approved"


# ── Non-admin access should be forbidden ─────────────────────────────────────

def test_non_admin_cannot_create_tenant():
    app = FastAPI()
    app.include_router(router)
    mock_user = make_non_admin_user()
    mock_db = AsyncMock()
    app.dependency_overrides[current_user] = lambda: mock_user
    app.dependency_overrides[get_current_tenant] = lambda: "test-tenant"
    app.dependency_overrides[get_db] = lambda: mock_db

    client = TestClient(app)
    response = client.post(
        "/api/v1/admin/tenants",
        json={"name": "Unauthorized Corp"},
    )

    assert response.status_code == 403
