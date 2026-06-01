"""Fixtures for agents tests."""

import os

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.app.models.activation_platform_mapping import Base as Base1
from backend.app.models.platform_config_template import Base as Base2


@pytest.fixture(autouse=True)
def mock_settings():
    """Mock settings to provide required configuration values."""
    settings_dict = {
        "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
        "SECRET_KEY": "test-secret-key-minimum-32-characters-long-12345",
        "ALGORITHM": "HS256",
        "ACCESS_TOKEN_EXPIRE_MINUTES": 30,
        "REFRESH_TOKEN_EXPIRE_DAYS": 7,
    }

    # Set environment variables
    for key, value in settings_dict.items():
        os.environ[key] = str(value)

    yield

    # Cleanup
    for key in settings_dict.keys():
        if key in os.environ:
            del os.environ[key]


@pytest_asyncio.fixture
async def db_session():
    """Create an async SQLAlchemy session for testing."""
    # Create in-memory SQLite database
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True
    )

    # Create tables from all model bases
    async with engine.begin() as conn:
        await conn.run_sync(Base1.metadata.create_all)
        await conn.run_sync(Base2.metadata.create_all)

    # Create session factory
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Create session for test
    async with async_session() as session:
        yield session
        await session.close()

    # Cleanup
    await engine.dispose()
