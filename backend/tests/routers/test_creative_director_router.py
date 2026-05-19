"""Endpoint tests for Creative Director router."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.routers.creative_director import router


def make_app():
    app = FastAPI()
    app.include_router(router)
    return app


def make_campaign_input():
    return {
        "campaign_id": "c-001",
        "tenant_id": "t-001",
        "objectives": ["brand_awareness", "lead_generation"],
        "target_audience": {
            "language": "en",
        },
        "brand_guidelines": {
            "tone": "playful",
            "colors": ["#FF5733"],
            "messaging_rules": ["be bold"],
            "mandatory_ctas": ["Shop Now"],
        },
        "platforms": ["instagram"],
        "product_details": "Premium sneakers for urban athletes",
        "campaign_theme": "Summer Freedom",
        "primary_cta": "Shop Now",
    }


# ── GET /api/agents/creative-director/health ─────────────────────────────────

def test_health_check_returns_200():
    app = make_app()
    with patch("backend.app.routers.creative_director.CreativeDirectorAgent") as MockAgent:
        instance = MagicMock()
        instance.generator = MagicMock()
        instance.validator = MagicMock()
        MockAgent.return_value = instance
        client = TestClient(app)
        response = client.get("/api/agents/creative-director/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


# ── POST /api/agents/creative-director/generate ──────────────────────────────

def test_generate_empty_platforms_returns_400():
    app = make_app()
    payload = make_campaign_input()
    payload["platforms"] = []
    client = TestClient(app)
    response = client.post("/api/agents/creative-director/generate", json=payload)
    assert response.status_code in (400, 422)


def test_generate_null_brand_guidelines_returns_400():
    app = make_app()
    payload = make_campaign_input()
    payload["brand_guidelines"] = None
    client = TestClient(app)
    response = client.post("/api/agents/creative-director/generate", json=payload)
    assert response.status_code in (400, 422)


def test_generate_happy_path_returns_200():
    app = make_app()

    from backend.app.agents.creative_director.models import CreativeDirectorOutput
    mock_output = MagicMock(spec=CreativeDirectorOutput)
    mock_output.metadata = MagicMock()
    mock_output.metadata.validation_status = "passed"
    mock_output.platforms = {"instagram": MagicMock()}
    mock_output.model_dump = MagicMock(return_value={
        "campaign_id": "c-001",
        "platforms": {},
        "metadata": {"validation_status": "passed", "generation_timestamp": "2026-01-01T00:00:00Z"},
    })

    with patch(
        "backend.app.routers.creative_director.creative_director_agent",
        new=AsyncMock(return_value=mock_output),
    ):
        client = TestClient(app)
        response = client.post(
            "/api/agents/creative-director/generate",
            json=make_campaign_input(),
        )

    assert response.status_code == 200


def test_generate_agent_exception_returns_500():
    app = make_app()

    with patch(
        "backend.app.routers.creative_director.creative_director_agent",
        new=AsyncMock(side_effect=RuntimeError("LLM timeout")),
    ):
        client = TestClient(app)
        response = client.post(
            "/api/agents/creative-director/generate",
            json=make_campaign_input(),
        )

    assert response.status_code == 500
