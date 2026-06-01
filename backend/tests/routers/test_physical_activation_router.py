"""Endpoint tests for physical activation router — M8 logging."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.core.auth import current_user
from backend.app.core.dependencies import get_current_tenant
from backend.app.core.models import User
from backend.app.db import get_db
from backend.app.routers.physical_activation import router


def make_mock_user():
    user = MagicMock(spec=User)
    user.id = "test-user-id"
    user.email = "test@example.com"
    user.is_active = True
    role = MagicMock()
    role.name = "platform_admin"
    user.role = role
    return user


def make_mock_log(activation_id: str = "act-001"):
    log = MagicMock()
    log.id = "log-001"
    log.tenant_id = "test-tenant"
    log.campaign_id = "camp-001"
    log.activation_id = activation_id
    log.event_type = "proof_of_execution"
    log.channel = "newspaper"
    log.payload = {"actual_cost": 42000.0, "vendor_name": "TOI"}
    log.logged_at = datetime(2026, 5, 21, tzinfo=UTC)
    log.created_at = datetime(2026, 5, 21, tzinfo=UTC)
    return log


def make_app():
    app = FastAPI()
    app.include_router(router)
    mock_user = make_mock_user()
    mock_db = AsyncMock()
    app.dependency_overrides[current_user] = lambda: mock_user
    app.dependency_overrides[get_current_tenant] = lambda: "test-tenant"
    app.dependency_overrides[get_db] = lambda: mock_db
    return app, mock_db


# ── POST /{activation_id}/log-physical ────────────────────────────────────────

def test_log_physical_activation_returns_201():
    app, mock_db = make_app()
    log = make_mock_log("act-001")

    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock(side_effect=lambda obj: None)

    with patch("backend.app.routers.physical_activation.PhysicalActivationLog") as MockLog:
        MockLog.return_value = log
        client = TestClient(app)
        response = client.post(
            "/api/v1/activations/act-001/log-physical",
            json={
                "campaign_id": "camp-001",
                "channel": "newspaper",
                "event_type": "proof_of_execution",
                "actual_run_date": "2026-05-21",
                "actual_cost": 42000.0,
                "vendor_name": "Times of India",
                "grp_circulation": "450000",
                "notes": "Page 3, full page",
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["activation_id"] == "act-001"
    assert body["channel"] == "newspaper"


# ── GET /{activation_id}/physical-logs ────────────────────────────────────────

def test_list_physical_logs_returns_logs():
    app, mock_db = make_app()
    log = make_mock_log("act-001")

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [log]
    mock_db.execute = AsyncMock(return_value=mock_result)

    client = TestClient(app)
    response = client.get("/api/v1/activations/act-001/physical-logs")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 1
    assert body[0]["activation_id"] == "act-001"


def test_list_physical_logs_empty():
    app, mock_db = make_app()

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    client = TestClient(app)
    response = client.get("/api/v1/activations/act-999/physical-logs")

    assert response.status_code == 200
    assert response.json() == []
