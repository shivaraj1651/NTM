"""Tests for creatives router — list, get, status update, approvals, revisions."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.core.auth import current_user
from backend.app.core.dependencies import get_current_tenant
from backend.app.core.models import User
from backend.app.db import get_db
from backend.app.routers.creatives import _campaign_media_to_creatives, router


def make_user():
    role = MagicMock()
    role.name = "creative_lead"
    user = MagicMock(spec=User)
    user.id = "user-001"
    user.role = role
    return user


def make_app():
    app = FastAPI()
    app.include_router(router)
    mock_db = AsyncMock()
    mock_user = make_user()
    app.dependency_overrides[current_user] = lambda: mock_user
    app.dependency_overrides[get_current_tenant] = lambda: "t-001"
    app.dependency_overrides[get_db] = lambda: mock_db
    return app, mock_db


def make_creative_mock(creative_id="cr-001", campaign_id="camp-001"):
    c = MagicMock()
    c.id = creative_id
    c.campaign_id = campaign_id
    c.tenant_id = "t-001"
    c.generation_id = "gen-001"
    c.platform = "instagram"
    c.creative_type = "image"
    c.content = {"url": "https://example.com/img.png", "asset_url": "https://example.com/img.png"}
    c.validation_status = "ai_draft"
    c.refinement_attempts = 0
    c.created_at = None
    c.updated_at = None
    c.to_dict.return_value = {
        "id": creative_id,
        "campaign_id": campaign_id,
        "tenant_id": "t-001",
        "generation_id": "gen-001",
        "platform": "instagram",
        "creative_type": "image",
        "content": c.content,
        "validation_status": "ai_draft",
        "refinement_attempts": 0,
        "created_at": None,
        "updated_at": None,
    }
    return c


# ── _campaign_media_to_creatives (pure function) ──────────────────────────────

def test_campaign_media_images():
    campaign = {
        "_id": "camp-001",
        "tenant_id": "t-001",
        "creative_assets": {
            "images": [
                {"id": "img-1", "url": "https://s3/img1.png", "format": "square"},
                {"id": "img-2", "url": "https://s3/img2.png", "format": "portrait"},
            ],
        },
    }
    result = _campaign_media_to_creatives(campaign)
    assert len(result) == 2
    assert result[0]["creative_type"] == "image"
    assert result[0]["id"] == "img-1"
    assert result[1]["platform"] == "portrait"


def test_campaign_media_audio():
    campaign = {
        "_id": "camp-001",
        "tenant_id": "t-001",
        "creative_assets": {
            "audio": [
                {"id": "aud-1", "url": "https://s3/audio.mp3", "format": "radio",
                 "voice_style": "warm", "duration_seconds": 30},
            ],
        },
    }
    result = _campaign_media_to_creatives(campaign)
    assert len(result) == 1
    assert result[0]["creative_type"] == "audio"
    assert result[0]["content"]["duration_seconds"] == 30
    assert result[0]["content"]["voice_style"] == "warm"


def test_campaign_media_video():
    campaign = {
        "_id": "camp-001",
        "tenant_id": "t-001",
        "creative_assets": {
            "video": [
                {"id": "vid-1", "url": "https://s3/video.mp4", "format": "social_video",
                 "duration_seconds": 15, "status": "complete"},
            ],
        },
    }
    result = _campaign_media_to_creatives(campaign)
    assert len(result) == 1
    assert result[0]["creative_type"] == "video"
    assert result[0]["content"]["duration_seconds"] == 15


def test_campaign_media_skips_missing_url():
    campaign = {
        "_id": "camp-001",
        "tenant_id": "t-001",
        "creative_assets": {
            "images": [
                {"id": "img-1"},  # no url
                {"url": "https://s3/ok.png"},  # no id
                {"id": "img-3", "url": "https://s3/valid.png", "format": "square"},
            ],
        },
    }
    result = _campaign_media_to_creatives(campaign)
    assert len(result) == 1
    assert result[0]["id"] == "img-3"


def test_campaign_media_approved_status():
    campaign = {
        "_id": "c",
        "tenant_id": "t",
        "creative_assets": {
            "images": [
                {"id": "i1", "url": "http://x", "approved": True},
                {"id": "i2", "url": "http://y", "approved": False},
                {"id": "i3", "url": "http://z"},
            ],
        },
    }
    result = _campaign_media_to_creatives(campaign)
    assert result[0]["validation_status"] == "internal_approved"
    assert result[1]["validation_status"] == "revision_requested"
    assert result[2]["validation_status"] == "ai_draft"


def test_campaign_media_empty_assets():
    campaign = {"_id": "c", "tenant_id": "t", "creative_assets": {}}
    result = _campaign_media_to_creatives(campaign)
    assert result == []


def test_campaign_media_no_creative_assets():
    campaign = {"_id": "c", "tenant_id": "t"}
    result = _campaign_media_to_creatives(campaign)
    assert result == []


def test_campaign_media_mixed():
    campaign = {
        "_id": "camp-mix",
        "tenant_id": "t-001",
        "created_at": "2026-06-01T00:00:00Z",
        "creative_assets": {
            "images": [{"id": "i1", "url": "http://img", "format": "wide"}],
            "audio": [{"id": "a1", "url": "http://aud"}],
            "video": [{"id": "v1", "url": "http://vid"}],
        },
    }
    result = _campaign_media_to_creatives(campaign)
    assert len(result) == 3
    types = {r["creative_type"] for r in result}
    assert types == {"image", "audio", "video"}


# ── GET /api/v1/creatives ────────────────────────────────────────────────────

def test_list_creatives_empty():
    app, db = make_app()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=result)

    with patch("backend.app.routers.creatives._mongo_creatives_for_tenant",
               return_value=[]):
        client = TestClient(app)
        response = client.get("/api/v1/creatives")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["creatives"] == []


def test_list_creatives_with_postgres_rows():
    app, db = make_app()
    creative = make_creative_mock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [creative]
    db.execute = AsyncMock(return_value=result)

    with patch("backend.app.routers.creatives._mongo_creatives_for_tenant",
               return_value=[]):
        client = TestClient(app)
        response = client.get("/api/v1/creatives")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["creatives"][0]["id"] == "cr-001"


def test_list_creatives_deduplicates_mongo():
    """MongoDB assets with same id as Postgres row are not duplicated."""
    app, db = make_app()
    creative = make_creative_mock("cr-shared")
    result = MagicMock()
    result.scalars.return_value.all.return_value = [creative]
    db.execute = AsyncMock(return_value=result)

    mongo_asset = {"id": "cr-shared", "creative_type": "image", "platform": "square"}

    with patch("backend.app.routers.creatives._mongo_creatives_for_tenant",
               return_value=[mongo_asset]):
        client = TestClient(app)
        response = client.get("/api/v1/creatives")

    body = response.json()
    assert body["total"] == 1


# ── GET /api/v1/creatives/{id} ────────────────────────────────────────────────

def test_get_creative_found_in_postgres():
    app, db = make_app()
    creative = make_creative_mock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = creative
    db.execute = AsyncMock(return_value=result)

    client = TestClient(app)
    response = client.get("/api/v1/creatives/cr-001")

    assert response.status_code == 200
    assert response.json()["id"] == "cr-001"


def test_get_creative_fallback_mongo():
    app, db = make_app()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)

    mongo_asset = {"id": "mongo-cr-1", "creative_type": "image", "platform": "square"}

    with patch("backend.app.routers.creatives._mongo_creatives_for_tenant",
               return_value=[mongo_asset]):
        client = TestClient(app)
        response = client.get("/api/v1/creatives/mongo-cr-1")

    assert response.status_code == 200
    assert response.json()["id"] == "mongo-cr-1"


def test_get_creative_not_found():
    app, db = make_app()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)

    with patch("backend.app.routers.creatives._mongo_creatives_for_tenant",
               return_value=[]):
        client = TestClient(app)
        response = client.get("/api/v1/creatives/nonexistent")

    assert response.status_code == 404


# ── PATCH /api/v1/creatives/{id}/status ──────────────────────────────────────

def test_update_creative_status_postgres():
    app, db = make_app()
    creative = make_creative_mock()
    select_result = MagicMock()
    select_result.scalar_one_or_none.return_value = creative
    update_result = MagicMock()
    db.execute = AsyncMock(side_effect=[select_result, update_result])
    db.commit = AsyncMock()

    client = TestClient(app)
    response = client.patch(
        "/api/v1/creatives/cr-001/status",
        json={"status": "internal_approved"},
    )

    assert response.status_code == 200
    assert response.json()["validation_status"] == "internal_approved"


def test_update_creative_status_mongo_only_asset():
    """Updating a MongoDB-only asset returns success without DB write."""
    app, db = make_app()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)

    client = TestClient(app)
    response = client.patch(
        "/api/v1/creatives/mongo-only-cr/status",
        json={"status": "client_approved"},
    )

    assert response.status_code == 200
    assert response.json()["validation_status"] == "client_approved"


# ── POST /api/v1/creatives/{id}/internal-approve ─────────────────────────────

def test_internal_approve_not_found():
    app, db = make_app()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)

    client = TestClient(app)
    response = client.post("/api/v1/creatives/cr-missing/internal-approve")

    assert response.status_code == 404


def test_internal_approve_success():
    app, db = make_app()
    creative = make_creative_mock()
    select_result = MagicMock()
    select_result.scalar_one_or_none.return_value = creative
    update_result = MagicMock()
    db.execute = AsyncMock(side_effect=[select_result, update_result])
    db.commit = AsyncMock()

    client = TestClient(app)
    response = client.post("/api/v1/creatives/cr-001/internal-approve")

    assert response.status_code == 200
    assert response.json()["validation_status"] == "internal_approved"


# ── POST /api/v1/creatives/{id}/client-approve ───────────────────────────────

def test_client_approve_success():
    app, db = make_app()
    creative = make_creative_mock()
    select_result = MagicMock()
    select_result.scalar_one_or_none.return_value = creative
    update_result = MagicMock()
    db.execute = AsyncMock(side_effect=[select_result, update_result])
    db.commit = AsyncMock()

    client = TestClient(app)
    response = client.post("/api/v1/creatives/cr-001/client-approve")

    assert response.status_code == 200
    assert response.json()["validation_status"] == "client_approved"


def test_client_approve_not_found():
    app, db = make_app()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)

    client = TestClient(app)
    response = client.post("/api/v1/creatives/missing/client-approve")

    assert response.status_code == 404


# ── POST /api/v1/creatives/{id}/request-revision ─────────────────────────────

def test_request_revision_success():
    app, db = make_app()
    creative = make_creative_mock()
    creative.refinement_attempts = 1
    creative.content = {"url": "http://x"}
    select_result = MagicMock()
    select_result.scalar_one_or_none.return_value = creative
    update_result = MagicMock()
    db.execute = AsyncMock(side_effect=[select_result, update_result])
    db.commit = AsyncMock()

    client = TestClient(app)
    response = client.post(
        "/api/v1/creatives/cr-001/request-revision",
        json={"comment": "Please make it brighter"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["validation_status"] == "revision_requested"
    assert body["refinement_attempts"] == 2
    assert body["comment"] == "Please make it brighter"


def test_request_revision_not_found():
    app, db = make_app()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)

    client = TestClient(app)
    response = client.post(
        "/api/v1/creatives/missing/request-revision",
        json={"comment": "Not found"},
    )

    assert response.status_code == 404


# ── GET /api/v1/creatives/{id}/download ──────────────────────────────────────

def test_download_creative_postgres():
    app, db = make_app()
    creative = make_creative_mock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = creative
    db.execute = AsyncMock(return_value=result)

    client = TestClient(app)
    response = client.get("/api/v1/creatives/cr-001/download")

    assert response.status_code == 200
    assert "asset_url" in response.json()


def test_download_creative_no_url():
    app, db = make_app()
    creative = make_creative_mock()
    creative.content = {}  # no url
    result = MagicMock()
    result.scalar_one_or_none.return_value = creative
    db.execute = AsyncMock(return_value=result)

    client = TestClient(app)
    response = client.get("/api/v1/creatives/cr-001/download")

    assert response.status_code == 404


def test_download_creative_not_found():
    app, db = make_app()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)

    with patch("backend.app.routers.creatives._mongo_creatives_for_tenant",
               return_value=[]):
        client = TestClient(app)
        response = client.get("/api/v1/creatives/ghost/download")

    assert response.status_code == 404


def test_download_creative_from_mongo():
    app, db = make_app()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)

    mongo_asset = {
        "id": "mongo-vid-1",
        "creative_type": "video",
        "platform": "social_video",
        "content": {"url": "https://s3/video.mp4"},
    }

    with patch("backend.app.routers.creatives._mongo_creatives_for_tenant",
               return_value=[mongo_asset]):
        client = TestClient(app)
        response = client.get("/api/v1/creatives/mongo-vid-1/download")

    assert response.status_code == 200
    assert response.json()["asset_url"] == "https://s3/video.mp4"
