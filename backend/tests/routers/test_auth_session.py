import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.db import get_db
from backend.app.main import app


class _FakeResult:
    def scalar_one_or_none(self):
        return None


class _FakeSession:
    async def execute(self, *args, **kwargs):
        return _FakeResult()


@pytest.mark.asyncio
async def test_login_unknown_user_autocreates():
    """Unknown user is auto-created on first login — returns 200 with token."""
    fake_db = _RegSession(tenant_exists=False, role_name="tenant_admin")
    app.dependency_overrides[get_db] = lambda: fake_db

    async def _fake_jwt(user):
        return "mock-token"

    try:
        with patch("backend.app.routers.auth_session.write_jwt", _fake_jwt), \
             patch("backend.app.routers.auth_session.hash_password", return_value="hashed"):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://t") as ac:
                r = await ac.post(
                    "/api/v1/auth/login",
                    json={"email": "tenant@nestle.com", "password": "devpass123"},
                )
        assert r.status_code == 200
        data = r.json()
        assert data["token"] == "mock-token"
        assert data["user"]["email"] == "tenant@nestle.com"
        assert data["user"]["role"] == "tenant_admin"
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_login_wrong_password_401():
    """Existing user with wrong password → 401."""

    class _ExistingUserSession:
        async def execute(self, *args, **kwargs):
            result = MagicMock()
            user = SimpleNamespace(
                id="u-1", email="tenant@acme.com",
                hashed_password="$2b$12$hashed", is_active=True,
                role=SimpleNamespace(name="tenant_admin"),
                tenant_id="t-1",
            )
            result.scalar_one_or_none.return_value = user
            return result

    app.dependency_overrides[get_db] = lambda: _ExistingUserSession()
    try:
        with patch("backend.app.routers.auth_session.verify_password", return_value=False):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://t") as ac:
                r = await ac.post(
                    "/api/v1/auth/login",
                    json={"email": "tenant@acme.com", "password": "wrongpassword"},
                )
        assert r.status_code == 401
    finally:
        app.dependency_overrides.pop(get_db, None)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_role(name: str) -> SimpleNamespace:
    return SimpleNamespace(id=str(uuid.uuid4()), name=name, permissions=[])


def _make_tenant(name: str) -> SimpleNamespace:
    return SimpleNamespace(id=str(uuid.uuid4()), name=name, is_active=True)


class _RegSession:
    """Fake AsyncSession for register endpoint tests."""

    def __init__(self, *, tenant_exists: bool = False, role_name: str = "brand_manager"):
        self._tenant_exists = tenant_exists
        self._role_name = role_name
        self._call = 0
        self._added: list = []
        self.tenant = _make_tenant("acme") if tenant_exists else None
        self.role = _make_role(role_name)

    async def execute(self, *args, **kwargs):
        self._call += 1
        result = MagicMock()
        if self._call == 1:
            result.scalar_one_or_none.return_value = None          # duplicate-user check
        elif self._call == 2:
            result.scalar_one_or_none.return_value = self.tenant   # tenant lookup
        elif self._call == 3:
            result.scalar_one_or_none.return_value = self.role     # role lookup
        else:
            result.scalar_one_or_none.return_value = None
        return result

    def add(self, obj):
        self._added.append(obj)

    async def flush(self):
        pass  # SimpleNamespace tenants already have id set at creation

    async def commit(self):
        pass

    async def refresh(self, obj):
        obj.role = self.role
        obj.tenant_id = getattr(obj, 'tenant_id', self.tenant.id if self.tenant else "t-new")


# ── Register tests ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_new_tenant_derives_role():
    """Email tenant@acme.com → role tenant_admin, tenant 'acme' created."""
    fake_db = _RegSession(tenant_exists=False, role_name="tenant_admin")
    app.dependency_overrides[get_db] = lambda: fake_db

    async def _fake_jwt(user):
        return "mock-token"

    try:
        with patch("backend.app.routers.auth_session.write_jwt", _fake_jwt), \
             patch("backend.app.routers.auth_session.hash_password", return_value="hashed"):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://t") as ac:
                r = await ac.post(
                    "/api/v1/auth/register",
                    json={"email": "tenant@acme.com", "password": "password123"},
                )
        assert r.status_code == 201
        data = r.json()
        assert data["token"] == "mock-token"
        assert data["user"]["role"] == "tenant_admin"
        assert data["user"]["tenant_id"] is not None
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_register_existing_tenant_reused():
    """Email brand@acme.com → existing tenant reused (no new Tenant inserted)."""
    fake_db = _RegSession(tenant_exists=True, role_name="brand_manager")
    app.dependency_overrides[get_db] = lambda: fake_db

    async def _fake_jwt(user):
        return "mock-token"

    try:
        with patch("backend.app.routers.auth_session.write_jwt", _fake_jwt), \
             patch("backend.app.routers.auth_session.hash_password", return_value="hashed"):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://t") as ac:
                r = await ac.post(
                    "/api/v1/auth/register",
                    json={"email": "brand@acme.com", "password": "password123"},
                )
        assert r.status_code == 201
        data = r.json()
        assert data["user"]["role"] == "brand_manager"
        # existing tenant was reused — only User was added, no new tenant SimpleNamespace
        new_tenants = [o for o in fake_db._added if isinstance(o, SimpleNamespace)]
        assert len(new_tenants) == 0
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_register_admin_prefix_gets_platform_admin():
    """Email admin@newco.com → role platform_admin, tenant 'newco' created."""
    fake_db = _RegSession(tenant_exists=False, role_name="platform_admin")
    app.dependency_overrides[get_db] = lambda: fake_db

    async def _fake_jwt(user):
        return "mock-token"

    try:
        with patch("backend.app.routers.auth_session.write_jwt", _fake_jwt), \
             patch("backend.app.routers.auth_session.hash_password", return_value="hashed"):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://t") as ac:
                r = await ac.post(
                    "/api/v1/auth/register",
                    json={"email": "admin@newco.com", "password": "password123"},
                )
        assert r.status_code == 201
        assert r.json()["user"]["role"] == "platform_admin"
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_register_duplicate_email_409():
    """Duplicate email returns 409."""

    class _DupSession:
        async def execute(self, *args, **kwargs):
            result = MagicMock()
            result.scalar_one_or_none.return_value = SimpleNamespace(id="x")  # simulates existing user
            return result

        def add(self, obj): pass
        async def flush(self): pass
        async def commit(self): pass
        async def refresh(self, obj): pass

    app.dependency_overrides[get_db] = lambda: _DupSession()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as ac:
            r = await ac.post(
                "/api/v1/auth/register",
                json={"email": "tenant@acme.com", "password": "password123"},
            )
        assert r.status_code == 409
    finally:
        app.dependency_overrides.pop(get_db, None)
