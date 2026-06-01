from contextvars import ContextVar
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from backend.app.core.dependencies import get_current_tenant, require_role, tenant_context
from backend.app.core.models import UserRole


def test_tenant_context_is_context_var():
    """tenant_context should be a ContextVar"""
    assert isinstance(tenant_context, ContextVar)


@pytest.mark.asyncio
async def test_get_current_tenant_returns_context_value():
    """get_current_tenant falls back to tenant_context when request.state has no tenant_id"""
    from types import SimpleNamespace
    request = MagicMock()
    request.state = SimpleNamespace()  # no tenant_id attribute -> falls back to context
    token = tenant_context.set("tenant-123")
    try:
        tenant_id = await get_current_tenant(request)
        assert tenant_id == "tenant-123"
    finally:
        tenant_context.reset(token)


@pytest.mark.asyncio
async def test_get_current_tenant_prefers_request_state():
    """get_current_tenant returns request.state.tenant_id when present"""
    from types import SimpleNamespace
    request = MagicMock()
    request.state = SimpleNamespace(tenant_id="tenant-from-state")
    tenant_id = await get_current_tenant(request)
    assert tenant_id == "tenant-from-state"


@pytest.mark.asyncio
async def test_get_current_tenant_empty_context():
    """get_current_tenant returns None if neither request.state nor context is set"""
    from types import SimpleNamespace
    request = MagicMock()
    request.state = SimpleNamespace()
    tenant_id = await get_current_tenant(request)
    assert tenant_id is None


def make_user(role_name: str):
    user = MagicMock()
    user.role = MagicMock()
    user.role.name = role_name
    return user


@pytest.mark.asyncio
async def test_require_role_allows_matching_role():
    user = make_user("brand_manager")
    dep = require_role([UserRole.BRAND_MANAGER, UserRole.CMO])
    result = await dep(user=user)
    assert result is user


@pytest.mark.asyncio
async def test_require_role_blocks_non_matching_role():
    user = make_user("viewer")
    dep = require_role([UserRole.BRAND_MANAGER, UserRole.CMO])
    with pytest.raises(HTTPException) as exc_info:
        await dep(user=user)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_role_allows_platform_admin_when_listed():
    user = make_user("platform_admin")
    dep = require_role([UserRole.PLATFORM_ADMIN])
    result = await dep(user=user)
    assert result is user


@pytest.mark.asyncio
async def test_require_role_blocks_when_role_is_none():
    user = make_user("viewer")
    user.role = None
    dep = require_role([UserRole.BRAND_MANAGER])
    with pytest.raises(HTTPException) as exc_info:
        await dep(user=user)
    assert exc_info.value.status_code == 403
