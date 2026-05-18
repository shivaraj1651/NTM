"""Fixtures for models tests."""

import pytest
import pytest_asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from sqlalchemy import MetaData
from backend.app.models.activation_platform_mapping import Base as Base1
from backend.app.models.platform_config_template import Base as Base2
from backend.app.models.kpi import Base as Base3
from backend.app.models.client import Base as Base4
from backend.app.models.mandate import Base as Base5
from backend.app.models.campaign import Base as Base6
from backend.app.models.campaign_concept import Base as Base7
from backend.app.models.activation import Base as Base8
from backend.app.models.budget import Base as Base9
from backend.app.models.approval_log import Base as Base10


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
        await conn.run_sync(Base3.metadata.create_all)
        await conn.run_sync(Base4.metadata.create_all)
        await conn.run_sync(Base5.metadata.create_all)
        await conn.run_sync(Base6.metadata.create_all)
        await conn.run_sync(Base7.metadata.create_all)
        await conn.run_sync(Base8.metadata.create_all)
        await conn.run_sync(Base9.metadata.create_all)
        await conn.run_sync(Base10.metadata.create_all)

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
