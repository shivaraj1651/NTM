import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from backend.app.models.base import Base
import backend.app.core.models  # noqa: F401  registers User/Role/Tenant/user_tenant_access
import backend.app.models.mandate  # noqa: F401  registers mandates
from backend.app.scripts.seed import seed_all, TENANT_ID


@pytest_asyncio.fixture
async def shared_factory(monkeypatch):
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Seed once
    async with factory() as session:
        await seed_all(session)

    # Point BOTH the db module and the middleware's imported name at this factory
    monkeypatch.setattr("backend.app.db.get_session_local", lambda: factory)
    monkeypatch.setattr("backend.app.core.middleware.get_session_local", lambda: factory)
    yield factory
    await engine.dispose()


async def test_login_then_list_mandates(shared_factory):
    from backend.app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as ac:
        r = await ac.post("/api/v1/auth/login", json={"email": "admin@acme.test", "password": "devpass123"})
        assert r.status_code == 200, r.text
        token = r.json()["token"]
        assert r.json()["user"]["role"] == "platform_admin"
        assert r.json()["user"]["tenant_id"] == TENANT_ID

        headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": TENANT_ID}
        r2 = await ac.get("/api/v1/mandates", headers=headers)
        assert r2.status_code == 200, r2.text
        assert isinstance(r2.json(), list)

        # negative: missing tenant header -> 400
        r3 = await ac.get("/api/v1/mandates", headers={"Authorization": f"Bearer {token}"})
        assert r3.status_code == 400, r3.text
