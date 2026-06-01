"""Tests for routers/__init__.py register_routers()."""

from fastapi import FastAPI


def test_register_routers_adds_mandate_routes():
    from backend.app.routers import register_routers
    app = FastAPI()
    register_routers(app)
    paths = {route.path for route in app.routes}
    assert "/api/v1/mandates/{mandate_id}/analyze-competitors" in paths
    assert "/api/v1/jobs/{job_id}" in paths


def test_register_routers_adds_campaign_routes():
    from backend.app.routers import register_routers
    app = FastAPI()
    register_routers(app)
    paths = {route.path for route in app.routes}
    assert "/api/v1/campaigns" in paths
    assert "/api/v1/campaigns/{campaign_id}" in paths
    assert "/api/v1/campaigns/{campaign_id}/confirm" in paths
    assert "/api/v1/campaigns/{campaign_id}/activation-plan" in paths
    assert "/api/v1/campaigns/{campaign_id}/approve-budget" in paths
    assert "/api/v1/campaigns/{campaign_id}/confirm-budget" in paths


def test_register_routers_adds_creative_director_routes():
    from backend.app.routers import register_routers
    app = FastAPI()
    register_routers(app)
    paths = {route.path for route in app.routes}
    assert "/api/agents/creative-director/generate" in paths
    assert "/api/agents/creative-director/health" in paths
