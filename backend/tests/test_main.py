"""Tests for backend/app/main.py."""

import pytest
from starlette.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("SECRET_KEY", "testsecretkey_at_least_32_chars_long!!")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:3000")
    import sys
    sys.modules.pop("backend.app.main", None)
    import backend.app.main as main_module
    return TestClient(main_module.app, raise_server_exceptions=False)


def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_health_returns_status_ok(client):
    response = client.get("/health")
    assert response.json() == {"status": "ok"}


def test_cors_header_present_for_allowed_origin(client):
    response = client.get(
        "/health",
        headers={"Origin": "http://localhost:3000"},
    )
    assert "access-control-allow-origin" in response.headers


def test_mandate_route_registered(client):
    paths = {route.path for route in client.app.routes}
    assert "/api/v1/mandates/{mandate_id}/analyze-competitors" in paths


def test_campaign_route_registered(client):
    paths = {route.path for route in client.app.routes}
    assert "/api/v1/campaigns" in paths


def test_creative_director_route_registered(client):
    paths = {route.path for route in client.app.routes}
    assert "/api/agents/creative-director/generate" in paths


def test_auth_login_route_registered(client):
    paths = {route.path for route in client.app.routes}
    assert "/api/v1/auth/jwt/login" in paths
