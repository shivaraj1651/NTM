"""Unit tests for AuditMiddleware."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.app.core.audit_context import get_audit_context, set_audit_context
from backend.app.core.audit_middleware import AuditMiddleware


def _make_request(user=None, tenant_id=None, client_host="1.2.3.4"):
    request = MagicMock()
    request.state = MagicMock()
    request.state.user = user
    request.state.tenant_id = tenant_id
    request.client = MagicMock()
    request.client.host = client_host
    return request


def _make_user(user_id="u-1", role_name="campaign_manager"):
    user = MagicMock()
    user.id = user_id
    user.role = MagicMock()
    user.role.name = role_name
    return user


@pytest.mark.asyncio
async def test_sets_audit_context_when_user_present():
    set_audit_context(None)
    user = _make_user("u-1", "tenant_admin")
    request = _make_request(user=user, tenant_id="t-1")
    call_next = AsyncMock(return_value=MagicMock())

    middleware = AuditMiddleware(app=AsyncMock())
    await middleware.dispatch(request, call_next)

    ctx = get_audit_context()
    assert ctx is not None
    assert ctx.actor_id == "u-1"
    assert ctx.actor_role == "tenant_admin"
    assert ctx.tenant_id == "t-1"
    assert ctx.ip_address == "1.2.3.4"
    call_next.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_skips_context_when_no_user():
    set_audit_context(None)
    request = _make_request(user=None, tenant_id=None)
    call_next = AsyncMock(return_value=MagicMock())

    middleware = AuditMiddleware(app=AsyncMock())
    await middleware.dispatch(request, call_next)

    assert get_audit_context() is None
    call_next.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_handles_user_with_no_role():
    set_audit_context(None)
    user = MagicMock()
    user.id = "u-2"
    user.role = None
    request = _make_request(user=user, tenant_id="t-2")
    call_next = AsyncMock(return_value=MagicMock())

    middleware = AuditMiddleware(app=AsyncMock())
    await middleware.dispatch(request, call_next)

    ctx = get_audit_context()
    assert ctx is not None
    assert ctx.actor_role is None
