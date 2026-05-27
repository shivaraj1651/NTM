"""Endpoint tests for replanning router."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.routers.replanning import router, get_db
from backend.app.core.auth import current_user
from backend.app.core.dependencies import get_current_tenant
from backend.app.core.models import User


def make_mock_user():
    user = MagicMock(spec=User)
    user.id = "test-user-id"
    user.email = "test@example.com"
    user.is_active = True
    user.tenant_id = "test-tenant"
    _role = MagicMock()
    _role.name = "platform_admin"
    user.role = _role
    return user


def make_app():
    app = FastAPI()
    app.include_router(router)
    mock_user = make_mock_user()
    app.dependency_overrides[current_user] = lambda: mock_user
    app.dependency_overrides[get_current_tenant] = lambda: "test-tenant"
    app.dependency_overrides[get_db] = lambda: MagicMock()
    return app


def make_svc_mock(**method_returns):
    svc = MagicMock()
    for method, retval in method_returns.items():
        if isinstance(retval, Exception):
            setattr(svc, method, AsyncMock(side_effect=retval))
        else:
            setattr(svc, method, AsyncMock(return_value=retval))
    return svc


# ── POST /api/v1/campaigns/{campaign_id}/replan ──────────────────────────────

def test_replan_campaign_returns_job_queued():
    app = make_app()
    campaign_doc = {
        "_id": "camp-001",
        "tenant_id": "test-tenant",
        "mandate_id": "mand-001",
        "status": "approved",
    }
    svc = make_svc_mock(get=campaign_doc)

    with patch("backend.app.routers.replanning.CampaignService", return_value=svc), \
         patch("backend.app.routers.replanning.run_weekly_replan_task") as mock_task:
        client = TestClient(app)
        response = client.post("/api/v1/campaigns/camp-001/replan")

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert body["campaign_id"] == "camp-001"
    assert "job_id" in body
    mock_task.delay.assert_called_once_with("mand-001")
