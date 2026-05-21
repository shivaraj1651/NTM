"""WhatsApp Business Cloud API tool — send campaign notification messages."""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_WHATSAPP_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
_WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
_WA_AVAILABLE = bool(_WHATSAPP_TOKEN and _WHATSAPP_PHONE_ID)

_GRAPH_URL = "https://graph.facebook.com/v18.0"


class WhatsAppTool:
    """Wraps WhatsApp Business Cloud API for sending template and text messages."""

    async def send_message(self, to: str, message: str) -> dict:
        if not _WA_AVAILABLE:
            logger.warning("WhatsApp not configured — mock send to %s: %.60s", to, message)
            return {"status": "mock", "to": to, "message": message}

        import httpx

        url = f"{_GRAPH_URL}/{_WHATSAPP_PHONE_ID}/messages"
        headers = {
            "Authorization": f"Bearer {_WHATSAPP_TOKEN}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": message},
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def send_approval_request(
        self,
        to: str,
        entity_type: str,
        entity_id: str,
        approval_url: Optional[str] = None,
    ) -> dict:
        """Send a structured approval-gate notification."""
        lines = [f"NTM: Action required — {entity_type} is ready for your approval."]
        lines.append(f"Reference ID: {entity_id}")
        if approval_url:
            lines.append(f"Review here: {approval_url}")
        return await self.send_message(to, "\n".join(lines))

    async def send_campaign_live_alert(self, to: str, campaign_name: str) -> dict:
        return await self.send_message(to, f"NTM: Campaign '{campaign_name}' is now LIVE.")

    async def send_kpi_red_alert(self, to: str, kpi_name: str, current: float, target: float) -> dict:
        msg = (
            f"NTM KPI ALERT: {kpi_name} has fallen below threshold. "
            f"Current: {current:.2f} | Target: {target:.2f}. "
            "Log in to review and approve replan recommendations."
        )
        return await self.send_message(to, msg)
