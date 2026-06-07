"""Unit tests for Razorpay signature verification (no network)."""
import hashlib
import hmac

from app.core.config import Settings
from app.services.payment_service import PaymentService


def _service(secret="rzp_secret"):
    settings = Settings(razorpay_key_id="rzp_test_x", razorpay_key_secret=secret)
    return PaymentService(settings, order_service=None)  # _verify_signature ignores orders


def test_valid_signature_accepted():
    svc = _service()
    order_id, payment_id = "order_ABC", "pay_XYZ"
    sig = hmac.new(b"rzp_secret", f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()
    assert svc._verify_signature(order_id, payment_id, sig) is True


def test_tampered_signature_rejected():
    svc = _service()
    assert svc._verify_signature("order_ABC", "pay_XYZ", "deadbeef") is False


def test_webhook_signature_roundtrip():
    settings = Settings(razorpay_webhook_secret="whsec")
    svc = PaymentService(settings, order_service=None)
    body = b'{"event":"payment.captured"}'
    sig = hmac.new(b"whsec", body, hashlib.sha256).hexdigest()
    assert svc.verify_webhook(body, sig) is True
    assert svc.verify_webhook(body, "bad") is False
