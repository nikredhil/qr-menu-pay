"""Phone OTP issuing + verification.

Demo mode (default) keeps codes in memory and returns them in the API response
so the flow is testable without an SMS provider. To send real SMS, plug a
provider into ``_deliver`` and set ``otp_demo_mode=false``.
"""
from __future__ import annotations

import secrets
import time
from dataclasses import dataclass

from app.core.config import Settings
from app.core.logging import get_logger

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
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._pending: dict[str, _Pending] = {}

    def _generate(self) -> str:
        digits = self._settings.otp_length
        return "".join(secrets.choice("0123456789") for _ in range(digits))

    def _deliver(self, phone: str, code: str) -> None:
        """Send the code. In demo mode this only logs; wire SMS here for prod."""
        if self._settings.otp_demo_mode:
            logger.info("otp_demo", phone=phone, code=code)
            return
        # e.g. Twilio / MSG91 call would go here. Until configured, log loudly.
        logger.warning("otp_no_provider", phone=phone)

    def request(self, phone: str, name: str | None) -> tuple[int, str | None]:
        """Issue a code for ``phone``. Returns (ttl_seconds, debug_otp|None)."""
        code = self._generate()
        ttl = self._settings.otp_ttl_seconds
        self._pending[phone] = _Pending(
            code=code, expires_at=time.time() + ttl, name=name
        )
        self._deliver(phone, code)
        debug_otp = code if self._settings.otp_demo_mode else None
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
