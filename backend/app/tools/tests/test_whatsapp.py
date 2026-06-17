"""Tests for the WhatsApp Business Cloud API tool."""
import os
from unittest.mock import AsyncMock, patch

import pytest

from backend.app.tools.whatsapp import WhatsAppTool


@pytest.mark.asyncio
async def test_send_message_mock_mode_when_unconfigured():
    with patch.dict(os.environ, {"WHATSAPP_ACCESS_TOKEN": "", "WHATSAPP_PHONE_NUMBER_ID": ""}, clear=False), \
         patch("backend.app.tools.whatsapp._WA_AVAILABLE", False):
        tool = WhatsAppTool()
        result = await tool.send_message("+1234567890", "Hello from NTM")
    assert result["status"] == "mock"
    assert result["to"] == "+1234567890"
    assert result["message"] == "Hello from NTM"


@pytest.mark.asyncio
async def test_send_message_live_calls_api():
    fake_response = {"messages": [{"id": "wamid.abc123"}]}

    with patch("backend.app.tools.whatsapp._WA_AVAILABLE", True), \
         patch("backend.app.tools.whatsapp._WHATSAPP_TOKEN", "wa-token"), \
         patch("backend.app.tools.whatsapp._WHATSAPP_PHONE_ID", "phone-001"), \
         patch("httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_resp = AsyncMock()
        mock_resp.json = lambda: fake_response
        mock_resp.raise_for_status = lambda: None
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_cls.return_value.__aenter__.return_value = mock_client

        tool = WhatsAppTool()
        result = await tool.send_message("+447700123456", "Campaign live!")

    assert result == fake_response
    assert mock_client.post.called
    payload = mock_client.post.call_args[1]["json"]
    assert payload["to"] == "+447700123456"
    assert payload["type"] == "text"
    assert payload["text"]["body"] == "Campaign live!"


@pytest.mark.asyncio
async def test_send_approval_request_contains_required_lines():
    with patch("backend.app.tools.whatsapp._WA_AVAILABLE", False):
        tool = WhatsAppTool()
        result = await tool.send_approval_request(
            to="+1234567890",
            entity_type="Mandate",
            entity_id="mand-001",
            approval_url="https://ntm.example.com/review",
        )
    assert result["status"] == "mock"
    assert "Mandate" in result["message"]
    assert "mand-001" in result["message"]
    assert "https://ntm.example.com/review" in result["message"]


@pytest.mark.asyncio
async def test_send_approval_request_without_url():
    with patch("backend.app.tools.whatsapp._WA_AVAILABLE", False):
        tool = WhatsAppTool()
        result = await tool.send_approval_request(
            to="+1234567890",
            entity_type="Campaign",
            entity_id="camp-001",
        )
    assert "camp-001" in result["message"]
    assert "https://" not in result["message"]


@pytest.mark.asyncio
async def test_send_campaign_live_alert():
    with patch("backend.app.tools.whatsapp._WA_AVAILABLE", False):
        tool = WhatsAppTool()
        result = await tool.send_campaign_live_alert("+1234567890", "Summer Sale 2026")
    assert "Summer Sale 2026" in result["message"]
    assert "LIVE" in result["message"]


@pytest.mark.asyncio
async def test_send_kpi_red_alert_formats_numbers():
    with patch("backend.app.tools.whatsapp._WA_AVAILABLE", False):
        tool = WhatsAppTool()
        result = await tool.send_kpi_red_alert("+1234567890", kpi_name="CTR", current=0.85, target=2.0)
    assert "CTR" in result["message"]
    assert "0.85" in result["message"]
    assert "2.00" in result["message"]


@pytest.mark.asyncio
async def test_send_kpi_red_alert_mentions_threshold():
    with patch("backend.app.tools.whatsapp._WA_AVAILABLE", False):
        tool = WhatsAppTool()
        result = await tool.send_kpi_red_alert("+1234567890", "ROAS", 1.2, 3.0)
    assert "threshold" in result["message"].lower() or "below" in result["message"].lower()
