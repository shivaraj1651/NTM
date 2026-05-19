"""Endpoint tests for mandate router."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.routers.mandate import router, get_db
from backend.app.core.auth import current_user
from backend.app.core.dependencies import get_current_tenant
from backend.app.core.models import User


def make_mock_user():
    user = MagicMock(spec=User)
    user.id = "test-user-id"
    user.email = "test@example.com"
    user.is_active = True
    return user


def make_mock_db(mandate=None, client_profile=None, job_report=None):
    def make_col(find_one_result):
        col = MagicMock()
        col.find_one = AsyncMock(return_value=find_one_result)
        col.insert_one = AsyncMock(return_value=MagicMock())
        return col

    db = MagicMock()
    db.__getitem__ = MagicMock(side_effect=lambda name: {
        "mandates": make_col(mandate),
        "clients": make_col(client_profile),
        "ci_reports": make_col(job_report),
    }.get(name, make_col(None)))
    return db


def make_app(mock_db=None):
    app = FastAPI()
    app.include_router(router)
    mock_user = make_mock_user()
    app.dependency_overrides[current_user] = lambda: mock_user
    app.dependency_overrides[get_current_tenant] = lambda: "test-tenant"
    if mock_db is not None:
        app.dependency_overrides[get_db] = lambda: mock_db
    return app


# ── POST /api/v1/mandates/{mandate_id}/analyze-competitors ───────────────────

def test_analyze_competitors_mandate_not_found_returns_404():
    db = make_mock_db(mandate=None)
    app = make_app(mock_db=db)
    client = TestClient(app)
    response = client.post(f"/api/v1/mandates/{uuid4()}/analyze-competitors")
    assert response.status_code == 404


def test_analyze_competitors_missing_client_id_returns_404():
    mandate = {"_id": "m-001", "tenant_id": "test-tenant"}  # no client_id
    db = make_mock_db(mandate=mandate, client_profile=None)
    app = make_app(mock_db=db)
    client = TestClient(app)
    response = client.post(f"/api/v1/mandates/{uuid4()}/analyze-competitors")
    assert response.status_code == 404


def test_analyze_competitors_invalid_uuid_returns_422():
    app = make_app()
    client = TestClient(app)
    response = client.post("/api/v1/mandates/not-a-uuid/analyze-competitors")
    assert response.status_code == 422


# ── GET /api/v1/jobs/{job_id} ─────────────────────────────────────────────────

def test_get_job_not_found_returns_404():
    db = make_mock_db(job_report=None)
    app = make_app(mock_db=db)
    client = TestClient(app)
    response = client.get(f"/api/v1/jobs/{uuid4()}")
    assert response.status_code == 404


def test_get_job_invalid_uuid_returns_422():
    app = make_app()
    client = TestClient(app)
    response = client.get("/api/v1/jobs/not-a-uuid")
    assert response.status_code == 422


# ── NEW: CRUD + lifecycle endpoint tests ──────────────────────────────────────


def make_mock_sql_session():
    return MagicMock()


def make_svc_mock(**method_returns):
    svc = MagicMock()
    for method, retval in method_returns.items():
        if isinstance(retval, Exception):
            setattr(svc, method, AsyncMock(side_effect=retval))
        else:
            setattr(svc, method, AsyncMock(return_value=retval))
    return svc


def make_app_with_sql(mock_mongo_db=None, mock_sql_session=None):
    from backend.app.routers.mandate import router, get_db, get_sql_db
    app = FastAPI()
    app.include_router(router)
    mock_user = make_mock_user()
    app.dependency_overrides[current_user] = lambda: mock_user
    app.dependency_overrides[get_current_tenant] = lambda: "test-tenant"
    if mock_mongo_db is not None:
        app.dependency_overrides[get_db] = lambda: mock_mongo_db
    if mock_sql_session is not None:
        app.dependency_overrides[get_sql_db] = lambda: mock_sql_session
    return app


# ── POST /api/v1/mandates ─────────────────────────────────────────────────────

def test_create_mandate_returns_201():
    app = make_app_with_sql(mock_sql_session=make_mock_sql_session())
    mandate_payload = {
        "name": "Summer Campaign",
        "client_id": "c-001",
        "objective": "Brand awareness",
        "region": "EMEA",
        "total_budget": 100000.0,
        "currency": "USD",
        "start_date": "2026-06-01",
        "end_date": "2026-12-31",
    }
    svc = make_svc_mock(create={"id": "m-new", "status": "draft", "tenant_id": "test-tenant"})
    with patch("backend.app.routers.mandate.MandateService", return_value=svc), \
         patch("backend.app.routers.mandate.run_mandate_analysis") as mock_task:
        mock_task.delay = MagicMock()
        client = TestClient(app)
        response = client.post("/api/v1/mandates", json=mandate_payload)
    assert response.status_code == 201
    mock_task.delay.assert_called_once_with("m-new", "test-tenant")


def test_create_mandate_missing_required_field_returns_422():
    app = make_app_with_sql(mock_sql_session=make_mock_sql_session())
    with patch("backend.app.routers.mandate.MandateService"):
        client = TestClient(app)
        response = client.post("/api/v1/mandates", json={"name": "Incomplete"})
    assert response.status_code == 422


# ── GET /api/v1/mandates/{mandate_id} ────────────────────────────────────────

def test_get_mandate_returns_200():
    from fastapi import HTTPException
    app = make_app_with_sql(mock_sql_session=make_mock_sql_session())
    svc = make_svc_mock(get={"id": "m-001", "status": "draft", "tenant_id": "test-tenant"})
    with patch("backend.app.routers.mandate.MandateService", return_value=svc):
        client = TestClient(app)
        response = client.get("/api/v1/mandates/m-001")
    assert response.status_code == 200


def test_get_mandate_not_found_returns_404():
    from fastapi import HTTPException
    app = make_app_with_sql(mock_sql_session=make_mock_sql_session())
    svc = make_svc_mock(get=HTTPException(status_code=404, detail="Not found"))
    with patch("backend.app.routers.mandate.MandateService", return_value=svc):
        client = TestClient(app)
        response = client.get("/api/v1/mandates/nonexistent")
    assert response.status_code == 404


# ── PUT /api/v1/mandates/{mandate_id} ────────────────────────────────────────

def test_update_mandate_returns_200():
    app = make_app_with_sql(mock_sql_session=make_mock_sql_session())
    svc = make_svc_mock(update={"id": "m-001", "status": "draft", "name": "Updated"})
    with patch("backend.app.routers.mandate.MandateService", return_value=svc):
        client = TestClient(app)
        response = client.put("/api/v1/mandates/m-001", json={"name": "Updated"})
    assert response.status_code == 200


def test_update_mandate_non_draft_returns_409():
    from fastapi import HTTPException
    app = make_app_with_sql(mock_sql_session=make_mock_sql_session())
    svc = make_svc_mock(update=HTTPException(status_code=409, detail="Conflict"))
    with patch("backend.app.routers.mandate.MandateService", return_value=svc):
        client = TestClient(app)
        response = client.put("/api/v1/mandates/m-001", json={"name": "Late Update"})
    assert response.status_code == 409


# ── POST /api/v1/mandates/{mandate_id}/confirm ───────────────────────────────

def test_confirm_mandate_returns_200():
    app = make_app_with_sql(mock_sql_session=make_mock_sql_session())
    svc = make_svc_mock(confirm={"id": "m-001", "status": "confirmed"})
    with patch("backend.app.routers.mandate.MandateService", return_value=svc), \
         patch("backend.app.routers.mandate.run_campaign_strategy") as mock_task:
        mock_task.delay = MagicMock()
        client = TestClient(app)
        response = client.post("/api/v1/mandates/m-001/confirm")
    assert response.status_code == 200
    mock_task.delay.assert_called_once_with("m-001", "test-tenant")


def test_confirm_mandate_not_analyzed_returns_400():
    from fastapi import HTTPException
    app = make_app_with_sql(mock_sql_session=make_mock_sql_session())
    svc = make_svc_mock(confirm=HTTPException(status_code=400, detail="Not analyzed"))
    with patch("backend.app.routers.mandate.MandateService", return_value=svc):
        client = TestClient(app)
        response = client.post("/api/v1/mandates/m-001/confirm")
    assert response.status_code == 400


# ── GET /api/v1/mandates/{mandate_id}/summary-card ───────────────────────────

def test_get_summary_card_returns_200():
    mongo_db = make_mock_db()
    app = make_app_with_sql(mock_mongo_db=mongo_db, mock_sql_session=make_mock_sql_session())
    svc = make_svc_mock(get_summary_card={"mandate_id": "m-001", "score": 90})
    with patch("backend.app.routers.mandate.MandateService", return_value=svc):
        client = TestClient(app)
        response = client.get("/api/v1/mandates/m-001/summary-card")
    assert response.status_code == 200


def test_get_summary_card_not_available_returns_404():
    from fastapi import HTTPException
    mongo_db = make_mock_db()
    app = make_app_with_sql(mock_mongo_db=mongo_db, mock_sql_session=make_mock_sql_session())
    svc = make_svc_mock(get_summary_card=HTTPException(status_code=404, detail="Not available"))
    with patch("backend.app.routers.mandate.MandateService", return_value=svc):
        client = TestClient(app)
        response = client.get("/api/v1/mandates/m-001/summary-card")
    assert response.status_code == 404
