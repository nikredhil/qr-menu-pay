"""The production config guard rejects insecure / demo defaults."""
from app.core.config import Settings


def test_insecure_defaults_flagged():
    # Pass the insecure values explicitly so the test is independent of the
    # ambient env the test harness sets.
    s = Settings(
        environment="prod",
        jwt_secret="dev-secret-change-me",
        admin_password="hsrclub-admin",
        cors_origins="*",
        otp_demo_mode=True,
    )
    errors = s.production_errors()
    blob = " ".join(errors)
    assert "JWT_SECRET" in blob
    assert "ADMIN_PASSWORD" in blob
    assert "CORS_ORIGINS" in blob
    # In production this must be a real product: demo OTP and the unconfigured
    # (demo) payment gateway are boot-blocking, not just warnings.
    assert "OTP_DEMO_MODE" in blob
    assert "Razorpay" in blob


def _secure(**overrides) -> Settings:
    base = dict(
        environment="prod",
        jwt_secret="a-very-long-random-secret-value-0123456789",
        admin_password="a-strong-password",
        cors_origins="https://dine.hsrclub.in",
        otp_demo_mode=False,
        razorpay_key_id="rzp_live_xxx",
        razorpay_key_secret="secret_xxx",
    )
    base.update(overrides)
    return Settings(**base)


def test_secure_config_passes():
    assert _secure().production_errors() == []


def test_demo_otp_blocks_production():
    assert any("OTP_DEMO_MODE" in e for e in _secure(otp_demo_mode=True).production_errors())


def test_missing_razorpay_blocks_production():
    errors = _secure(razorpay_key_id=None, razorpay_key_secret=None).production_errors()
    assert any("Razorpay" in e for e in errors)
