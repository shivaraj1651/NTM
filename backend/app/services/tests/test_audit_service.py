"""Unit tests for AuditService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.core.audit_context import AuditContext, set_audit_context
from backend.app.services.audit_service import AuditService


def _make_session(commit_raises=None):
    """Return a mock session where add() is sync and commit() is async."""
    session = MagicMock()
    if commit_raises:
        session.commit = AsyncMock(side_effect=commit_raises)
    else:
        session.commit = AsyncMock()
    return session


def _make_session_factory(session):
    """Build a mock factory whose async context manager yields `session`."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)
    factory = MagicMock(return_value=cm)
    return factory


@pytest.mark.asyncio
async def test_emit_writes_row_when_context_set():
    set_audit_context(AuditContext(
        actor_id="u-1", actor_role="campaign_manager",
        tenant_id="t-1", ip_address="10.0.0.1",
    ))
    mock_session = _make_session()
    with patch("backend.app.services.audit_service.get_session_local",
               return_value=_make_session_factory(mock_session)):
        await AuditService().emit("mandate", "m-1", "create")

    mock_session.add.assert_called_once()
    row = mock_session.add.call_args[0][0]
    assert row.entity_type == "mandate"
    assert row.entity_id == "m-1"
    assert row.action == "create"
    assert row.actor_id == "u-1"
    assert row.actor_role == "campaign_manager"
    assert row.tenant_id == "t-1"
    assert row.status == "success"
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_emit_noop_without_context():
    set_audit_context(None)
    # Should return early without touching the DB at all
    with patch("backend.app.services.audit_service.get_session_local") as mock_factory:
        await AuditService().emit("mandate", "m-1", "create")
    mock_factory.assert_not_called()


@pytest.mark.asyncio
async def test_emit_swallows_db_errors():
    set_audit_context(AuditContext(
        actor_id="u-1", actor_role=None, tenant_id="t-1", ip_address=None,
    ))
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(side_effect=Exception("DB connection failed"))
    cm.__aexit__ = AsyncMock(return_value=False)
    factory = MagicMock(return_value=cm)
    with patch("backend.app.services.audit_service.get_session_local", return_value=factory):
        await AuditService().emit("campaign", "c-1", "create")  # must not raise


@pytest.mark.asyncio
async def test_emit_passes_payload_after():
    set_audit_context(AuditContext(
        actor_id="u-2", actor_role="tenant_admin",
        tenant_id="t-2", ip_address=None,
    ))
    mock_session = _make_session()
    payload = {"name": "Spring Launch", "budget": 50000}
    with patch("backend.app.services.audit_service.get_session_local",
               return_value=_make_session_factory(mock_session)):
        await AuditService().emit("mandate", "m-2", "update", payload_after=payload)

    row = mock_session.add.call_args[0][0]
    assert row.payload_after == payload
    assert row.payload_before is None


@pytest.mark.asyncio
async def test_emit_uses_provided_status():
    set_audit_context(AuditContext(
        actor_id="u-3", actor_role=None, tenant_id="t-3", ip_address=None,
    ))
    mock_session = _make_session()
    with patch("backend.app.services.audit_service.get_session_local",
               return_value=_make_session_factory(mock_session)):
        await AuditService().emit("campaign", "c-2", "activate", status="failed")

    row = mock_session.add.call_args[0][0]
    assert row.status == "failed"
