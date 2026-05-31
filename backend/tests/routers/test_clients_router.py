"""Endpoint tests for the client onboarding router (POST /api/v1/clients)."""

from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.routers.clients import router, get_sql_db, get_mongo_db
from backend.app.core.auth import current_user
from backend.app.core.dependencies import get_current_tenant
from backend.app.core.models import User


def make_mock_user(role_name="tenant_admin"):
    user = MagicMock(spec=User)
    user.id = "test-user-id"
    user.email = "test@example.com"
    user.is_active = True
    role = MagicMock()
    role.name = role_name
    user.role = role
    return user


def make_mock_sql_session():
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


def make_mock_mongo_db():
    col = MagicMock()
    col.replace_one = AsyncMock(return_value=MagicMock())
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=col)
    return db, col


def make_app(role_name="tenant_admin", sql_session=None, mongo_db=None):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[current_user] = lambda: make_mock_user(role_name)
    app.dependency_overrides[get_current_tenant] = lambda: "test-tenant"
    if sql_session is not None:
        app.dependency_overrides[get_sql_db] = lambda: sql_session
    if mongo_db is not None:
        app.dependency_overrides[get_mongo_db] = lambda: mongo_db
    return app


def test_create_client_returns_201_and_dual_writes_to_mongo():
    sql_session = make_mock_sql_session()
    mongo_db, clients_col = make_mock_mongo_db()
    app = make_app(sql_session=sql_session, mongo_db=mongo_db)
    client = TestClient(app)

    response = client.post(
        "/api/v1/clients",
        data={"org_name": "Acme", "industry": "Tech", "competitors": '["Foo", "Bar"]'},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["org_name"] == "Acme"
    assert body["industry"] == "Tech"
    assert body["tenant_id"] == "test-tenant"
    assert body["competitors"] == ["Foo", "Bar"]
    assert body["id"]
    # canonical SQL write
    sql_session.add.assert_called_once()
    sql_session.commit.assert_awaited_once()
    # dual-write bridge so Mongo readers (mandate analysis, competitive intel) resolve the client
    clients_col.replace_one.assert_awaited_once()
    _filter, doc = clients_col.replace_one.await_args.args[0], clients_col.replace_one.await_args.args[1]
    assert doc["_id"] == body["id"]
    assert doc["tenant_id"] == "test-tenant"


def test_create_client_missing_required_field_returns_422():
    app = make_app(sql_session=make_mock_sql_session(), mongo_db=make_mock_mongo_db()[0])
    client = TestClient(app)
    response = client.post("/api/v1/clients", data={"org_name": "NoIndustry"})
    assert response.status_code == 422


def test_create_client_forbidden_for_disallowed_role_returns_403():
    app = make_app(role_name="viewer", sql_session=make_mock_sql_session(), mongo_db=make_mock_mongo_db()[0])
    client = TestClient(app)
    response = client.post(
        "/api/v1/clients",
        data={"org_name": "Acme", "industry": "Tech"},
    )
    assert response.status_code == 403


def test_create_client_handles_empty_competitors():
    sql_session = make_mock_sql_session()
    mongo_db, _ = make_mock_mongo_db()
    app = make_app(sql_session=sql_session, mongo_db=mongo_db)
    client = TestClient(app)
    response = client.post(
        "/api/v1/clients",
        data={"org_name": "Acme", "industry": "Tech"},
    )
    assert response.status_code == 201
    assert response.json()["competitors"] == []
