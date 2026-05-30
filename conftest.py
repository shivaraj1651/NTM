"""
Root conftest.py for pytest configuration and shared fixtures.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytest_plugins = ["backend.tests.agents.conftest_evals"]

import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from backend.app.core.models import Base


@pytest.fixture(scope="session")
def event_loop_policy():
    """Set up event loop policy for async tests."""
    policy = asyncio.get_event_loop_policy()
    return policy


@pytest.fixture(scope="session")
async def async_engine(event_loop_policy):
    """Create an async SQLAlchemy engine for testing."""
    # Use SQLite in-memory for testing (fast, no external dependencies)
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def async_session(async_engine):
    """Provide a fresh async session for each test with clean database."""
    async_session_factory = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    # Clear all data before test
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        yield session
        await session.rollback()

    # Cleanup after test
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
