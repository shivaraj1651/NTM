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
async def test_login_unknown_user_401():
    app.dependency_overrides[get_db] = lambda: _FakeSession()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as ac:
            r = await ac.post("/api/v1/auth/login", json={"email": "nobody@x.com", "password": "x"})
        assert r.status_code == 401
    finally:
        app.dependency_overrides.pop(get_db, None)
