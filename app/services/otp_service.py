"""Phone OTP issuing + verification.

Codes are generated and verified here (so we own the TTL and attempt cap);
delivery is delegated to an :class:`SmsSender`. In demo mode the sender just
logs the code and the API echoes it back so the flow is testable without a real
phone; otherwise a real provider (Twilio / MSG91) sends the SMS.
"""
from __future__ import annotations

import secrets
import time
from dataclasses import dataclass

from app.core.config import Settings
from app.core.logging import get_logger
from app.services.sms import SmsSender

logger = get_logger(__name__)

# Allow at most this many verify attempts per issued code before it's burned.
_MAX_ATTEMPTS = 5


@dataclass
class _Pending:
    code: str
    expires_at: float
    name: str | None
    attempts: int = 0


class OtpError(Exception):
    pass


class OtpService:
    def __init__(self, settings: Settings, sender: SmsSender) -> None:
        self._settings = settings
        self._sender = sender
        self._pending: dict[str, _Pending] = {}

    def _generate(self) -> str:
        digits = self._settings.otp_length
        return "".join(secrets.choice("0123456789") for _ in range(digits))

    async def request(self, phone: str, name: str | None) -> tuple[int, str | None]:
        """Issue a code for ``phone``. Returns (ttl_seconds, debug_otp|None)."""
        code = self._generate()
        ttl = self._settings.otp_ttl_seconds
        self._pending[phone] = _Pending(
            code=code, expires_at=time.time() + ttl, name=name
        )
        try:
            await self._sender.send_otp(phone, code)
        except Exception as exc:  # provider/network failure — surface, don't hang
            logger.error("otp_send_failed", phone=phone, error=str(exc))
            raise OtpError("Couldn't send the code right now. Please try again.") from exc
        # Echo the code only when the demo sender is active.
        debug_otp = code if self._sender.is_demo else None
        return ttl, debug_otp

    def verify(self, phone: str, code: str) -> str | None:
        """Verify ``code`` for ``phone``. Returns the stored name on success."""
        pending = self._pending.get(phone)
        if pending is None:
            raise OtpError("Request a code first")
        if time.time() > pending.expires_at:
            del self._pending[phone]
            raise OtpError("Code expired — request a new one")
        if pending.attempts >= _MAX_ATTEMPTS:
            del self._pending[phone]
            raise OtpError("Too many attempts — request a new code")
        pending.attempts += 1
        if not secrets.compare_digest(pending.code, code.strip()):
            raise OtpError("Incorrect code")
        name = pending.name
        del self._pending[phone]  # one-time use
        return name
