"""SMS delivery for OTP codes, behind one small interface.

Three implementations: a no-network ``DemoSmsSender`` (logs the code, used in
demo mode), ``TwilioSmsSender`` (global), and ``Msg91SmsSender`` (India). The
factory picks one from settings and falls back to demo — with a warning — if the
selected provider isn't fully configured, so a misconfiguration degrades to a
testable state instead of a hard failure.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class SmsSender(ABC):
    # True for the demo sender, which means the API may echo the code back to the
    # client (so the flow is testable without a real phone).
    is_demo: bool = False

    @abstractmethod
    async def send_otp(self, phone: str, code: str) -> None:
        """Deliver ``code`` to a 10-digit Indian ``phone``. Raises on failure."""


class DemoSmsSender(SmsSender):
    is_demo = True

    async def send_otp(self, phone: str, code: str) -> None:
        logger.info("otp_demo", phone=phone, code=code)


class TwilioSmsSender(SmsSender):
    def __init__(self, sid: str, token: str, from_number: str, app_name: str) -> None:
        self._sid = sid
        self._token = token
        self._from = from_number
        self._app = app_name

    async def send_otp(self, phone: str, code: str) -> None:
        body = f"{code} is your {self._app} verification code. It expires shortly."
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self._sid}/Messages.json"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                url,
                data={"From": self._from, "To": f"+91{phone}", "Body": body},
                auth=(self._sid, self._token),
            )
        resp.raise_for_status()


class Msg91SmsSender(SmsSender):
    def __init__(
        self, auth_key: str, template_id: str, otp_var: str, sender_id: str | None
    ) -> None:
        self._auth_key = auth_key
        self._template_id = template_id
        self._var = otp_var
        self._sender_id = sender_id

    async def send_otp(self, phone: str, code: str) -> None:
        # MSG91 Flow API: the DLT template text is fixed server-side; we supply the
        # recipient and the code as the template's variable (default name "otp").
        payload: dict = {
            "template_id": self._template_id,
            "recipients": [{"mobiles": f"91{phone}", self._var: code}],
        }
        if self._sender_id:
            payload["sender"] = self._sender_id
        headers = {"authkey": self._auth_key, "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://control.msg91.com/api/v5/flow/", json=payload, headers=headers
            )
        resp.raise_for_status()


def build_sms_sender(settings: Settings) -> SmsSender:
    """Choose an SMS sender from settings, falling back to demo on misconfig."""
    if settings.otp_demo_mode:
        return DemoSmsSender()

    if settings.otp_provider == "twilio":
        if settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_from_number:
            return TwilioSmsSender(
                settings.twilio_account_sid,
                settings.twilio_auth_token,
                settings.twilio_from_number,
                settings.app_name,
            )
        logger.warning("otp_provider_unconfigured", provider="twilio")
        return DemoSmsSender()

    if settings.otp_provider == "msg91":
        if settings.msg91_auth_key and settings.msg91_template_id:
            return Msg91SmsSender(
                settings.msg91_auth_key,
                settings.msg91_template_id,
                settings.msg91_otp_var,
                settings.msg91_sender_id,
            )
        logger.warning("otp_provider_unconfigured", provider="msg91")
        return DemoSmsSender()

    return DemoSmsSender()
