# backend/tests/routers/test_digital_activator_router.py
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from backend.app.routers.digital_activator import router, get_db
from backend.app.core.auth import current_user
from backend.app.core.dependencies import get_current_tenant
from backend.app.core.models import User


def make_mock_user():
    user = MagicMock(spec=User)
    user.id = "user-1"
    user.email = "test@example.com"
    user.is_active = True
    user.tenant_id = "tenant-001"
    _role = MagicMock()
    _role.name = "platform_admin"
    user.role = _role
    return user


def make_app():
    app = FastAPI()
    app.include_router(router)
    mock_user = make_mock_user()
    app.dependency_overrides[current_user] = lambda: mock_user
    app.dependency_overrides[get_current_tenant] = lambda: "tenant-001"
    app.dependency_overrides[get_db] = lambda: MagicMock()
    return app


_MOCK_CAMPAIGN_DOC = {
    "_id": "camp-001",
    "mandate_id": "mand-001",
    "tenant_id": "tenant-001",
    "status": "approved",
    "concepts": [],
    "selected_concept_id": None,
    "activation_plan": [
        {"id": "act-001", "channel": "google_ads", "budget": 500},
        {"id": "act-002", "channel": "meta_ads", "budget": 300},
    ],
    "budget_proposal": None,
    "created_at": "2026-01-01T00:00:00",
    "updated_at": "2026-01-01T00:00:00",
}


def test_activate_campaign_returns_job_queued():
    from unittest.mock import patch, MagicMock

    app = make_app()
    svc = MagicMock()
    svc.get = AsyncMock(return_value=_MOCK_CAMPAIGN_DOC)

    mock_google = MagicMock()
    mock_google.delay = MagicMock()
    mock_meta = MagicMock()
    mock_meta.delay = MagicMock()
    mock_li = MagicMock()
    mock_li.delay = MagicMock()

    fake_map = {
        "google_ads": mock_google,
        "meta_ads": mock_meta,
        "linkedin_ads": mock_li,
    }

    with (
        patch("backend.app.routers.digital_activator.CampaignService", return_value=svc),
        patch("backend.app.routers.digital_activator._PLATFORM_TASK_MAP", fake_map),
    ):
        client = TestClient(app)
        response = client.post(
            "/api/v1/campaigns/camp-001/activate",
            headers={"Authorization": "Bearer test", "X-Tenant-ID": "tenant-001"},
        )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert body["campaign_id"] == "camp-001"
    assert "job_id" in body
    mock_google.delay.assert_called_once()
    mock_meta.delay.assert_called_once()
    mock_li.delay.assert_not_called()


def test_activate_campaign_not_found():
    from unittest.mock import patch

    app = make_app()
    svc = MagicMock()
    svc.get = AsyncMock(side_effect=HTTPException(status_code=404, detail="Not found"))

    with patch("backend.app.routers.digital_activator.CampaignService", return_value=svc):
        client = TestClient(app)
        response = client.post(
            "/api/v1/campaigns/bad-id/activate",
            headers={"Authorization": "Bearer test", "X-Tenant-ID": "tenant-001"},
        )

    assert response.status_code == 404
