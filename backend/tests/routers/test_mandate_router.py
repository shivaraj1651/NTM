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
