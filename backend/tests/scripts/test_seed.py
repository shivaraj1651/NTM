import pytest
import pytest_asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from backend.app.models.base import Base
import backend.app.core.models  # noqa: F401  (registers User/Role/Tenant on Base.metadata)
from backend.app.core.models import User, Role, Tenant
from backend.app.scripts.seed import seed_all


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_seed_is_idempotent(db_session):
    await seed_all(db_session)
    await seed_all(db_session)  # second run must not duplicate
    roles = (await db_session.execute(select(func.count()).select_from(Role))).scalar()
    tenants = (await db_session.execute(select(func.count()).select_from(Tenant))).scalar()
    users = (await db_session.execute(select(func.count()).select_from(User))).scalar()
    assert roles == 7
    assert tenants >= 1
    assert users == 7
