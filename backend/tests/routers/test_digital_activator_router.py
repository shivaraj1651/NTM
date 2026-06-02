# backend/tests/routers/test_digital_activator_router.py
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from backend.app.core.auth import current_user
from backend.app.core.dependencies import get_current_tenant
from backend.app.core.models import User
from backend.app.routers.digital_activator import get_db, router


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
    mock_db = MagicMock()
    mock_db["campaigns"].update_one = AsyncMock(return_value=None)
    app.dependency_overrides[current_user] = lambda: mock_user
    app.dependency_overrides[get_current_tenant] = lambda: "tenant-001"
    app.dependency_overrides[get_db] = lambda: mock_db
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

_FAKE_GOOGLE_RESULT = {
    "campaign_id": "google-test-123",
    "ad_id": "ad-test-456",
    "status": "test_live",
    "test_mode": True,
    "error": None,
}

_FAKE_META_RESULT = {
    "campaign_id": "meta-test-789",
    "ad_set_id": "adset-test-001",
    "ad_id": "ad-test-002",
    "status": "test_live",
    "test_mode": True,
    "error": None,
}


def test_activate_campaign_returns_activation_results():
    """POST /activate returns activation_results synchronously — no Celery."""
    from unittest.mock import patch

    app = make_app()
    svc = MagicMock()
    svc.get = AsyncMock(return_value=_MOCK_CAMPAIGN_DOC)

    with (
        patch("backend.app.routers.digital_activator.CampaignService", return_value=svc),
        patch("backend.app.routers.digital_activator.activate_google", new_callable=AsyncMock, return_value=_FAKE_GOOGLE_RESULT),
        patch("backend.app.routers.digital_activator.activate_meta", new_callable=AsyncMock, return_value=_FAKE_META_RESULT),
    ):
        client = TestClient(app)
        response = client.post(
            "/api/v1/campaigns/camp-001/activate",
            headers={"Authorization": "Bearer test", "X-Tenant-ID": "tenant-001"},
        )

    assert response.status_code == 202
    body = response.json()
    assert body["campaign_id"] == "camp-001"
    assert "job_id" in body
    assert "activation_results" in body
    assert body["activation_results"]["google_ads"]["status"] == "test_live"
    assert body["activation_results"]["meta_ads"]["status"] == "test_live"
    assert body["activation_results"]["google_ads"]["campaign_id"] == "google-test-123"


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
