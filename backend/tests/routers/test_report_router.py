"""Endpoint tests for report router."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.routers.report import router, get_mongo_db
from backend.app.core.auth import current_user
from backend.app.core.dependencies import get_current_tenant
from backend.app.core.models import User
from backend.app.db import get_db


def make_mock_user():
    user = MagicMock(spec=User)
    user.id = "test-user-id"
    user.email = "test@example.com"
    user.is_active = True
    user.tenant_id = "tenant-001"
    return user


def make_app():
    app = FastAPI()
    app.include_router(router)
    mock_user = make_mock_user()
    app.dependency_overrides[current_user] = lambda: mock_user
    app.dependency_overrides[get_current_tenant] = lambda: "tenant-001"
    app.dependency_overrides[get_mongo_db] = lambda: MagicMock()
    app.dependency_overrides[get_db] = lambda: MagicMock()
    return app


def make_campaign_svc_mock(**method_returns):
    svc = MagicMock()
    for method, retval in method_returns.items():
        if isinstance(retval, Exception):
            setattr(svc, method, AsyncMock(side_effect=retval))
        else:
            setattr(svc, method, AsyncMock(return_value=retval))
    return svc


CAMPAIGN_DOC = {
    "_id": "camp-001",
    "tenant_id": "tenant-001",
    "mandate_id": "mand-001",
    "status": "confirmed",
}


# ── POST /api/v1/campaigns/{campaign_id}/report/generate ─────────────────────

def test_generate_report_returns_job_queued():
    app = make_app()
    svc = make_campaign_svc_mock(get=CAMPAIGN_DOC)

    with patch("backend.app.routers.report.CampaignService", return_value=svc), \
         patch("backend.app.routers.report.generate_daily_report_task") as mock_task:
        client = TestClient(app)
        response = client.post("/api/v1/campaigns/camp-001/report/generate")

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert body["campaign_id"] == "camp-001"
    assert "job_id" in body
    mock_task.delay.assert_called_once_with("mand-001", "tenant-001")


# ── GET /api/v1/campaigns/{campaign_id}/report ───────────────────────────────

def test_get_report_returns_404_when_missing():
    app = make_app()
    campaign_svc = make_campaign_svc_mock(get=CAMPAIGN_DOC)
    report_svc = MagicMock()
    report_svc.get_latest = AsyncMock(return_value=None)

    with patch("backend.app.routers.report.CampaignService", return_value=campaign_svc), \
         patch("backend.app.routers.report.ReportService", return_value=report_svc):
        client = TestClient(app)
        response = client.get("/api/v1/campaigns/camp-001/report")

    assert response.status_code == 404
    assert "report" in response.json()["detail"].lower()


def test_get_report_returns_report_when_found():
    app = make_app()
    campaign_svc = make_campaign_svc_mock(get=CAMPAIGN_DOC)

    mock_report = MagicMock()
    mock_report.mandate_id = "mand-001"
    mock_report.tenant_id = "tenant-001"
    mock_report.report_type = "daily"
    mock_report.period_start = "2026-05-20"
    mock_report.period_end = "2026-05-20"
    mock_report.report_json = {"summary": "All good"}

    report_svc = MagicMock()
    report_svc.get_latest = AsyncMock(return_value=mock_report)

    with patch("backend.app.routers.report.CampaignService", return_value=campaign_svc), \
         patch("backend.app.routers.report.ReportService", return_value=report_svc):
        client = TestClient(app)
        response = client.get("/api/v1/campaigns/camp-001/report")

    assert response.status_code == 200
    body = response.json()
    assert body["mandate_id"] == "mand-001"
    assert body["report_type"] == "daily"
    assert body["report_json"] == {"summary": "All good"}
