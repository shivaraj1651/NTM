"""Unit tests for DigitalActivatorAgent (AGT-12)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.agents.digital_activator import DigitalActivatorAgent


def make_activation(**kwargs):
    defaults = {
        "id": "act-001",
        "campaign_id": "camp-001",
        "tenant_id": "tenant-001",
        "status": "approved",
        "channel_enum": "google_ads",
        "audience_segment": "brand_aware",
    }
    defaults.update(kwargs)
    obj = SimpleNamespace(**defaults)
    obj.to_dict = lambda: {k: v for k, v in vars(obj).items() if not k.startswith("_") and k != "to_dict"}
    return obj


def make_agent():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=MagicMock())))
    return DigitalActivatorAgent(db), db


# ── stub mode ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_activate_stub_mode_returns_immediately():
    agent, _ = make_agent()
    activation = make_activation()
    with patch("backend.app.agents.digital_activator.stub_enabled", return_value=True):
        result = await agent.activate(activation, "https://example.com/img.jpg")
    assert result["status"] == "activation_queued"
    assert result["stub"] is True
    assert result["platforms"] == ["google_ads"]
    assert result["subtask_count"] == 1


@pytest.mark.asyncio
async def test_activate_stub_mode_skips_celery():
    agent, _ = make_agent()
    activation = make_activation()
    with patch("backend.app.agents.digital_activator.stub_enabled", return_value=True):
        with patch("backend.app.agents.digital_activator.chord") as mock_chord:
            await agent.activate(activation, "https://example.com/img.jpg")
    mock_chord.assert_not_called()


# ── validation ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_activate_raises_if_not_approved():
    agent, _ = make_agent()
    activation = make_activation(status="pending")
    with patch("backend.app.agents.digital_activator.stub_enabled", return_value=False):
        with pytest.raises(ValueError, match="approved"):
            await agent.activate(activation, "https://example.com/img.jpg")


@pytest.mark.asyncio
async def test_activate_raises_if_campaign_not_found():
    agent, db = make_agent()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    activation = make_activation()
    with patch("backend.app.agents.digital_activator.stub_enabled", return_value=False):
        with pytest.raises(ValueError, match="Campaign"):
            await agent.activate(activation, "https://example.com/img.jpg")


@pytest.mark.asyncio
async def test_activate_raises_if_platform_config_not_found():
    agent, _ = make_agent()
    activation = make_activation()
    with patch("backend.app.agents.digital_activator.stub_enabled", return_value=False):
        with patch.object(agent.platform_config_service, "get_platform_config", new=AsyncMock(return_value=None)):
            with pytest.raises(ValueError, match="platform config"):
                await agent.activate(activation, "https://example.com/img.jpg")


# ── chord dispatch ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_activate_dispatches_chord_for_google_ads():
    agent, _ = make_agent()
    activation = make_activation(channel_enum="google_ads")
    mock_config = MagicMock()
    mock_config.platform_targeting_json = {"targeting": "data"}

    with patch("backend.app.agents.digital_activator.stub_enabled", return_value=False):
        with patch.object(agent.platform_config_service, "get_platform_config", new=AsyncMock(return_value=mock_config)):
            with patch("backend.app.agents.digital_activator.chord") as mock_chord:
                with patch("backend.app.agents.digital_activator.group"):
                    with patch("backend.app.agents.digital_activator.platform_activate_google") as mock_task:
                        mock_task.s = MagicMock(return_value="sig-google")
                        result = await agent.activate(activation, "https://example.com/img.jpg")

    mock_chord.assert_called_once()
    assert result["status"] == "activation_queued"
    assert result["platforms"] == ["google_ads"]
    assert result["subtask_count"] == 1


@pytest.mark.asyncio
async def test_activate_dispatches_chord_for_meta_ads():
    agent, _ = make_agent()
    activation = make_activation(channel_enum="meta_ads")
    mock_config = MagicMock()
    mock_config.platform_targeting_json = {}

    with patch("backend.app.agents.digital_activator.stub_enabled", return_value=False):
        with patch.object(agent.platform_config_service, "get_platform_config", new=AsyncMock(return_value=mock_config)):
            with patch("backend.app.agents.digital_activator.chord") as mock_chord:
                with patch("backend.app.agents.digital_activator.group"):
                    with patch("backend.app.agents.digital_activator.platform_activate_meta") as mock_task:
                        mock_task.s = MagicMock(return_value="sig-meta")
                        result = await agent.activate(activation, "https://example.com/img.jpg")

    mock_chord.assert_called_once()
    assert result["platforms"] == ["meta_ads"]


@pytest.mark.asyncio
async def test_activate_dispatches_chord_for_linkedin_ads():
    agent, _ = make_agent()
    activation = make_activation(channel_enum="linkedin_ads")
    mock_config = MagicMock()
    mock_config.platform_targeting_json = {}

    with patch("backend.app.agents.digital_activator.stub_enabled", return_value=False):
        with patch.object(agent.platform_config_service, "get_platform_config", new=AsyncMock(return_value=mock_config)):
            with patch("backend.app.agents.digital_activator.chord") as mock_chord:
                with patch("backend.app.agents.digital_activator.group"):
                    with patch("backend.app.agents.digital_activator.platform_activate_linkedin") as mock_task:
                        mock_task.s = MagicMock(return_value="sig-li")
                        result = await agent.activate(activation, "https://example.com/img.jpg")

    mock_chord.assert_called_once()
    assert result["platforms"] == ["linkedin_ads"]


@pytest.mark.asyncio
async def test_activate_unknown_channel_returns_empty_platforms():
    agent, _ = make_agent()
    activation = make_activation(channel_enum="tiktok_ads")
    mock_config = MagicMock()
    mock_config.platform_targeting_json = {}

    with patch("backend.app.agents.digital_activator.stub_enabled", return_value=False):
        with patch.object(agent.platform_config_service, "get_platform_config", new=AsyncMock(return_value=mock_config)):
            result = await agent.activate(activation, "https://example.com/img.jpg")

    assert result["status"] == "activation_queued"
    assert result["platforms"] == []
    assert result["subtask_count"] == 0


# ── _map_channel_to_platforms ──────────────────────────────────────────────────

def test_map_google_ads():
    agent, _ = make_agent()
    assert agent._map_channel_to_platforms("google_ads") == ["google_ads"]

def test_map_meta_ads():
    agent, _ = make_agent()
    assert agent._map_channel_to_platforms("meta_ads") == ["meta_ads"]

def test_map_linkedin_ads():
    agent, _ = make_agent()
    assert agent._map_channel_to_platforms("linkedin_ads") == ["linkedin_ads"]

def test_map_unknown_channel_returns_empty():
    agent, _ = make_agent()
    assert agent._map_channel_to_platforms("tiktok") == []


# ── _build_platform_signature ──────────────────────────────────────────────────

def test_build_signature_google():
    agent, _ = make_agent()
    with patch("backend.app.agents.digital_activator.platform_activate_google") as mock_task:
        mock_task.s = MagicMock(return_value="sig")
        result = agent._build_platform_signature({}, "google_ads", {}, "url")
    assert result == "sig"
    mock_task.s.assert_called_once_with({}, {}, "url")

def test_build_signature_meta():
    agent, _ = make_agent()
    with patch("backend.app.agents.digital_activator.platform_activate_meta") as mock_task:
        mock_task.s = MagicMock(return_value="sig")
        result = agent._build_platform_signature({}, "meta_ads", {}, "url")
    assert result == "sig"

def test_build_signature_linkedin():
    agent, _ = make_agent()
    with patch("backend.app.agents.digital_activator.platform_activate_linkedin") as mock_task:
        mock_task.s = MagicMock(return_value="sig")
        result = agent._build_platform_signature({}, "linkedin_ads", {}, "url")
    assert result == "sig"

def test_build_signature_unknown_returns_none():
    agent, _ = make_agent()
    result = agent._build_platform_signature({}, "snapchat", {}, "url")
    assert result is None


# ── _to_dict ───────────────────────────────────────────────────────────────────

def test_to_dict_uses_to_dict_method():
    obj = MagicMock()
    obj.to_dict = MagicMock(return_value={"id": "x"})
    assert DigitalActivatorAgent._to_dict(obj) == {"id": "x"}

def test_to_dict_falls_back_to_vars():
    obj = SimpleNamespace(id="y", _private="skip")
    result = DigitalActivatorAgent._to_dict(obj)
    assert result["id"] == "y"
    assert "_private" not in result
