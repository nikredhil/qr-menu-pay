"""Best-effort order notifications to the diner (SMS or WhatsApp).

Fires when an order is placed and when it's served. Delivery is always
best-effort: a provider hiccup logs an error but never blocks the order or the
HTTP response. Free-text messages go over Twilio (SMS, or WhatsApp when a
whatsapp_from is set). When Twilio isn't configured the message is logged, so
the flow is observable in local dev without an account.
"""
from __future__ import annotations

import httpx

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class NotificationService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def _twilio_ready(self) -> bool:
        s = self._settings
        return bool(s.twilio_account_sid and s.twilio_auth_token)

    def _from_to(self, phone: str) -> tuple[str | None, str]:
        s = self._settings
        to = f"+91{phone}"
        if s.notify_channel == "whatsapp" and s.twilio_whatsapp_from:
            return s.twilio_whatsapp_from, f"whatsapp:{to}"
        return s.twilio_from_number, to

    async def _send(self, phone: str, body: str) -> None:
        s = self._settings
        from_, to = self._from_to(phone)
        if not (self._twilio_ready and from_):
            # No provider wired — log so it's visible locally.
            logger.info("notify_demo", to=to, body=body)
            return
        url = f"https://api.twilio.com/2010-04-01/Accounts/{s.twilio_account_sid}/Messages.json"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                url,
                data={"From": from_, "To": to, "Body": body},
                auth=(s.twilio_account_sid, s.twilio_auth_token),
            )
        resp.raise_for_status()

    async def _safe_send(self, phone: str, body: str, event: str) -> None:
        if not self._settings.order_notifications_enabled:
            return
        try:
            await self._send(phone, body)
        except Exception as exc:  # never let a notification failure surface
            logger.error("notify_failed", event=event, phone=phone, error=str(exc))

    async def order_placed(self, *, phone: str, code: str, table_label: str, total: float) -> None:
        await self._safe_send(
            phone,
            f"{self._settings.app_name}: order {code} placed for {table_label}. "
            f"Total ₹{total:.0f}. We'll let you know when it's ready.",
            event="order_placed",
        )

    async def order_served(self, *, phone: str, code: str, table_label: str) -> None:
        await self._safe_send(
            phone,
            f"{self._settings.app_name}: order {code} for {table_label} is served. Enjoy!",
            event="order_served",
        )
