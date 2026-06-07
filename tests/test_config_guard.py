"""The production config guard rejects insecure defaults."""
from app.core.config import Settings


def test_insecure_defaults_flagged():
    # Pass the insecure values explicitly so the test is independent of the
    # ambient env the test harness sets.
    s = Settings(
        environment="prod",
        jwt_secret="dev-secret-change-me",
        admin_password="hsrclub-admin",
        cors_origins="*",
    )
    errors = s.production_errors()
    blob = " ".join(errors)
    assert "JWT_SECRET" in blob
    assert "ADMIN_PASSWORD" in blob
    assert "CORS_ORIGINS" in blob


def test_secure_config_passes():
    s = Settings(
        environment="prod",
        jwt_secret="a-very-long-random-secret-value-0123456789",
        admin_password="a-strong-password",
        cors_origins="https://dine.hsrclub.in",
    )
    assert s.production_errors() == []


def test_warnings_flag_demo_otp_and_demo_payments():
    s = Settings(environment="prod", otp_demo_mode=True)
    warnings = " ".join(s.production_warnings())
    assert "OTP_DEMO_MODE" in warnings
    assert "Razorpay" in warnings
