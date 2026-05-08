import pytest
from contextvars import ContextVar
from backend.app.core.dependencies import get_current_tenant, tenant_context


def test_tenant_context_is_context_var():
    """tenant_context should be a ContextVar"""
    assert isinstance(tenant_context, ContextVar)


@pytest.mark.asyncio
async def test_get_current_tenant_returns_context_value():
    """get_current_tenant should return value from tenant_context"""
    token = tenant_context.set("tenant-123")
    try:
        tenant_id = await get_current_tenant()
        assert tenant_id == "tenant-123"
    finally:
        tenant_context.reset(token)


@pytest.mark.asyncio
async def test_get_current_tenant_empty_context():
    """get_current_tenant should return None if context not set"""
    tenant_id = await get_current_tenant()
    assert tenant_id is None
