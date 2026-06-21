"""Application settings, loaded from environment / .env file."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "HSR Club Dine"
    environment: Literal["local", "dev", "prod"] = "local"
    log_level: str = "INFO"

    # Allowed CORS origins. "*" (default) allows any origin — fine for local dev.
    cors_origins: str = "*"

    # Storage backend: "file" (durable JSON, default), "memory" (ephemeral), or
    # "sql" (async Postgres — needed for high-concurrency order writes; set
    # database_url). "file" serializes every write behind one process lock and
    # is fine only for a low order rate.
    db_backend: Literal["memory", "file", "sql"] = "file"
    data_dir: str = "./data"
    # Postgres connection URL for db_backend="sql" (e.g. a Neon pooled URL). The
    # plain libpq form Neon/Render give you works as-is; it's normalised to the
    # asyncpg driver internally.
    database_url: str | None = None

    # --- Auth (HS256 tokens this API issues) ---
    # Customers sign in with a phone OTP; staff sign in with the admin password.
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 12
    admin_password: str = "hsrclub-admin"

    # --- Rate limiting (per client IP + target, sliding window) ---
    # OTP requests: blunt SMS-bombing a single number and broad spraying.
    otp_request_rate_limit: int = 5
    otp_request_window_seconds: int = 600
    # OTP verify attempts: limit code guessing beyond the per-code attempt cap.
    otp_verify_rate_limit: int = 10
    otp_verify_window_seconds: int = 600
    # Admin login: blunt password brute-forcing.
    admin_login_rate_limit: int = 8
    admin_login_window_seconds: int = 300

    # --- Phone OTP ---
    # In demo mode the code is logged and returned in the request response so the
    # flow is testable with no SMS provider. Set otp_demo_mode=false and configure
    # a provider below to send real SMS.
    otp_demo_mode: bool = True
    otp_length: int = 6
    otp_ttl_seconds: int = 300

    # Which SMS provider to use when otp_demo_mode is false. If the chosen
    # provider's credentials are missing, the app falls back to demo mode (and
    # logs a warning) rather than silently failing to send.
    otp_provider: Literal["twilio", "msg91"] = "msg91"

    # Twilio (global). https://www.twilio.com/console
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_from_number: str | None = None  # E.164, e.g. +15551234567

    # MSG91 (India-focused, cheaper for Indian numbers). Uses the Flow API with a
    # DLT-approved template that has one variable for the code (named by
    # msg91_otp_var). https://control.msg91.com
    msg91_auth_key: str | None = None
    msg91_template_id: str | None = None
    msg91_sender_id: str | None = None
    msg91_otp_var: str = "otp"

    # --- Razorpay (cards + UPI: GPay / PhonePe / Paytm / netbanking) ---
    # When both keys are unset the app uses a built-in DEMO gateway that completes
    # the payment flow without moving real money. Add TEST keys for real Razorpay
    # Checkout in test mode; LIVE keys (post-KYC) to take real payments.
    razorpay_key_id: str | None = None
    razorpay_key_secret: str | None = None
    currency: str = "INR"
    # Secret for the Razorpay webhook (Dashboard → Settings → Webhooks). When set,
    # the /payments/razorpay/webhook endpoint verifies and honours payment events
    # so an order is still marked paid even if the customer's browser drops off
    # before the in-page confirmation runs.
    razorpay_webhook_secret: str | None = None

    # --- Order notifications (SMS / WhatsApp) ---
    # Best-effort messages to the customer when an order is placed and when it's
    # served. Reuses the same SMS provider as OTP; WhatsApp uses Twilio's
    # WhatsApp channel when a whatsapp_from number is set. Never blocks an order.
    order_notifications_enabled: bool = False
    notify_channel: Literal["sms", "whatsapp"] = "sms"
    twilio_whatsapp_from: str | None = None  # e.g. "whatsapp:+14155238886"

    # --- Menu languages (multi-language menu) ---
    # The primary language plus any additional languages diners can switch to.
    # Items carry per-language overrides in their ``translations`` map.
    default_language: str = "en"
    supported_languages: str = "en,hi,kn"  # comma-separated codes

    @property
    def languages(self) -> list[str]:
        return [c.strip() for c in self.supported_languages.split(",") if c.strip()]

    @property
    def razorpay_enabled(self) -> bool:
        return bool(self.razorpay_key_id and self.razorpay_key_secret)

    # Defaults that are fine for local dev but must never run in production.
    _INSECURE_JWT_SECRET = "dev-secret-change-me"
    _INSECURE_ADMIN_PASSWORD = "hsrclub-admin"

    def production_errors(self) -> list[str]:
        """Critical misconfigurations that must block boot when ENVIRONMENT=prod.

        In production this is a *real* product: no echoed OTP codes and no fake
        payment gateway. Demo OTP and an unconfigured Razorpay are therefore
        boot-blocking, not just warnings.
        """
        errors: list[str] = []
        if self.jwt_secret == self._INSECURE_JWT_SECRET:
            errors.append("JWT_SECRET is still the insecure default — set a strong random value.")
        if self.admin_password == self._INSECURE_ADMIN_PASSWORD:
            errors.append("ADMIN_PASSWORD is still the default — set a strong password.")
        if self.cors_origins.strip() == "*":
            errors.append("CORS_ORIGINS is '*' — set an explicit frontend allowlist.")
        if self.db_backend == "sql" and not self.database_url:
            errors.append("DB_BACKEND=sql but DATABASE_URL is unset.")
        if self.otp_demo_mode:
            errors.append(
                "OTP_DEMO_MODE is on — codes would be echoed to clients. "
                "Set OTP_DEMO_MODE=false and configure a real SMS provider (Twilio/MSG91)."
            )
        if not self.razorpay_enabled:
            errors.append(
                "Razorpay is not configured — the demo gateway must never run in production. "
                "Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET."
            )
        return errors

    def production_warnings(self) -> list[str]:
        """Non-fatal things worth flagging at boot in production."""
        warnings: list[str] = []
        if not self.razorpay_webhook_secret:
            warnings.append(
                "RAZORPAY_WEBHOOK_SECRET is unset — orders rely on in-page confirmation only; "
                "set it so a dropped browser still settles the order via webhook."
            )
        if not self.order_notifications_enabled:
            warnings.append(
                "ORDER_NOTIFICATIONS_ENABLED is off — customers won't get SMS/WhatsApp order updates."
            )
        return warnings


@lru_cache
def get_settings() -> Settings:
    """Cached singleton so settings are parsed once per process."""
    return Settings()
