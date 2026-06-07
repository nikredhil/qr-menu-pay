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

    # Storage backend: "file" (durable JSON, default) or "memory" (ephemeral).
    db_backend: Literal["memory", "file"] = "file"
    data_dir: str = "./data"

    # --- Auth (HS256 tokens this API issues) ---
    # Customers sign in with a phone OTP; staff sign in with the admin password.
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 12
    admin_password: str = "hsrclub-admin"

    # --- Phone OTP ---
    # In demo mode the code is logged and returned in the request response so the
    # flow is testable with no SMS provider. Wire a provider to send real SMS.
    otp_demo_mode: bool = True
    otp_length: int = 6
    otp_ttl_seconds: int = 300

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

    @property
    def razorpay_enabled(self) -> bool:
        return bool(self.razorpay_key_id and self.razorpay_key_secret)


@lru_cache
def get_settings() -> Settings:
    """Cached singleton so settings are parsed once per process."""
    return Settings()
