"""
Tests for FastAPI-Users authentication configuration.

Verifies JWT strategy setup, user database adapter, and auth dependencies.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.auth import get_user_db, fastapi_users, current_user


@pytest.mark.asyncio
async def test_get_user_db_is_callable(async_session: AsyncSession):
    """get_user_db should be a callable generator"""
    gen = get_user_db(async_session)
    assert hasattr(gen, "__aiter__")


def test_fastapi_users_configured():
    """fastapi_users should be configured"""
    assert fastapi_users is not None


def test_current_user_is_dependency():
    """current_user should be a dependency"""
    assert current_user is not None
