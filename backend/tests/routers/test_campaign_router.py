"""Endpoint tests for campaign router."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from backend.app.routers.campaign import router, get_db
from backend.app.core.auth import current_user
from backend.app.core.dependencies import get_current_tenant
from backend.app.core.models import User


def make_mock_user():
    user = MagicMock(spec=User)
    user.id = "test-user-id"
    user.email = "test@example.com"
    user.is_active = True
    user.tenant_id = "test-tenant"
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


# ── POST /api/v1/campaigns ────────────────────────────────────────────────────

def test_create_campaign_returns_201():
    from unittest.mock import patch
    app = make_app()
    svc = make_svc_mock(create={"id": "c-new", "tenant_id": "test-tenant", "status": "pending"})
    with patch("backend.app.routers.campaign.CampaignService", return_value=svc):
        client = TestClient(app)
        response = client.post("/api/v1/campaigns", json={"mandate_id": "m-001"})
    assert response.status_code == 201


def test_create_campaign_missing_mandate_id_returns_422():
    from unittest.mock import patch
    app = make_app()
    with patch("backend.app.routers.campaign.CampaignService"):
        client = TestClient(app)
        response = client.post("/api/v1/campaigns", json={})
    assert response.status_code == 422


# ── GET /api/v1/campaigns/{campaign_id} ──────────────────────────────────────

def test_get_campaign_returns_200():
    from unittest.mock import patch
    app = make_app()
    svc = make_svc_mock(get={"id": "c-001", "tenant_id": "test-tenant", "status": "pending"})
    with patch("backend.app.routers.campaign.CampaignService", return_value=svc):
        client = TestClient(app)
        response = client.get("/api/v1/campaigns/c-001")
    assert response.status_code == 200


def test_get_campaign_not_found_returns_404():
    from unittest.mock import patch
    app = make_app()
    svc = make_svc_mock(get=HTTPException(status_code=404, detail="Not found"))
    with patch("backend.app.routers.campaign.CampaignService", return_value=svc):
        client = TestClient(app)
        response = client.get("/api/v1/campaigns/nonexistent")
    assert response.status_code == 404


# ── POST /api/v1/campaigns/{campaign_id}/confirm ─────────────────────────────

def test_confirm_campaign_returns_200():
    from unittest.mock import patch
    app = make_app()
    svc = make_svc_mock(confirm={"id": "c-001", "status": "confirmed"})
    with patch("backend.app.routers.campaign.CampaignService", return_value=svc):
        client = TestClient(app)
        response = client.post(
            "/api/v1/campaigns/c-001/confirm",
            json={"selected_concept_id": "cc-001"},
        )
    assert response.status_code == 200


def test_confirm_missing_concept_id_returns_422():
    from unittest.mock import patch
    app = make_app()
    with patch("backend.app.routers.campaign.CampaignService"):
        client = TestClient(app)
        response = client.post("/api/v1/campaigns/c-001/confirm", json={})
    assert response.status_code == 422


# ── POST /api/v1/campaigns/{campaign_id}/approve-budget ──────────────────────

def test_approve_budget_returns_200():
    from unittest.mock import patch
    app = make_app()
    svc = make_svc_mock(propose_budget={"id": "c-001", "status": "budget_proposed"})
    with patch("backend.app.routers.campaign.CampaignService", return_value=svc):
        client = TestClient(app)
        response = client.post("/api/v1/campaigns/c-001/approve-budget", json={})
    assert response.status_code == 200
