from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.app.core.dependencies import current_user, get_current_tenant


class _Req:
    def __init__(self, **state):
        self.state = SimpleNamespace(**state)

@pytest.mark.asyncio
async def test_current_user_returns_state_user():
    user = SimpleNamespace(id="u1", email="a@b.c")
    assert await current_user(_Req(user=user)) is user

@pytest.mark.asyncio
async def test_current_user_missing_raises_401():
    with pytest.raises(HTTPException) as exc:
        await current_user(_Req())
    assert exc.value.status_code == 401

@pytest.mark.asyncio
async def test_get_current_tenant_reads_state():
    assert await get_current_tenant(_Req(tenant_id="tenant-acme")) == "tenant-acme"
