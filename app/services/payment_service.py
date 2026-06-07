"""Payment orchestration.

Supports two providers behind one interface:

* **razorpay** — used when ``RAZORPAY_KEY_ID``/``RAZORPAY_KEY_SECRET`` are set.
  Creates a Razorpay Order via their REST API, then verifies the HMAC-SHA256
  signature Razorpay Checkout returns on success. Works in test mode with test
  keys and in production with live keys. Razorpay Checkout natively offers UPI
  (Google Pay / PhonePe / Paytm), cards, and netbanking in one sheet.
* **demo** — the zero-config fallback. Mints a fake order id and lets the client
  confirm success/failure so the whole flow is exercisable with no credentials
  and no real money movement.

Cash is handled directly here too: the order is placed and left payable at the
counter, where staff confirm collection.
"""
from __future__ import annotations

import hashlib
import hmac

import httpx

from app.core.config import Settings
from app.core.logging import get_logger
from app.models.schemas.order import Order
from app.models.schemas.payment import PaymentIntent
from app.services.order_service import OrderService

logger = get_logger(__name__)

_RAZORPAY_API = "https://api.razorpay.com/v1"


class PaymentError(Exception):
    pass


class PaymentService:
    def __init__(self, settings: Settings, order_service: OrderService) -> None:
        self._settings = settings
        self._orders = order_service

    @property
    def provider(self) -> str:
        return "razorpay" if self._settings.razorpay_enabled else "demo"

    async def create_intent(self, order: Order) -> PaymentIntent:
        """Create a gateway order and return what the client needs to pay."""
        amount_paise = int(round(order.total * 100))
        common = dict(
            order_id=order.id,
            amount=amount_paise,
            currency=self._settings.currency,
            name=self._settings.app_name,
            description=f"Order {order.code} · {order.table_label}",
            prefill_contact=order.phone,
        )

        if not self._settings.razorpay_enabled:
            # Demo gateway: no network call, no real charge.
            return PaymentIntent(
                provider="demo",
                razorpay_order_id=f"demo_order_{order.id[:8]}",
                key_id=None,
                **common,
            )

        payload = {
            "amount": amount_paise,
            "currency": self._settings.currency,
            "receipt": order.code,
            "notes": {"order_id": order.id, "table": order.table_label},
        }
        auth = (self._settings.razorpay_key_id, self._settings.razorpay_key_secret)
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(f"{_RAZORPAY_API}/orders", json=payload, auth=auth)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("razorpay_order_failed", order=order.id, error=str(exc))
            raise PaymentError("Could not reach the payment gateway") from exc

        rzp = resp.json()
        # Remember the gateway order id on our order so an async webhook can map
        # the payment back even if the customer's browser never confirms.
        await self._orders.attach_gateway_order(order.id, rzp["id"])
        return PaymentIntent(
            provider="razorpay",
            razorpay_order_id=rzp["id"],
            key_id=self._settings.razorpay_key_id,
            **common,
        )

    def _verify_signature(self, rzp_order_id: str, rzp_payment_id: str, signature: str) -> bool:
        secret = (self._settings.razorpay_key_secret or "").encode()
        body = f"{rzp_order_id}|{rzp_payment_id}".encode()
        expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    async def confirm_razorpay(
        self, order: Order, rzp_order_id: str, rzp_payment_id: str, signature: str
    ) -> Order:
        if not self._settings.razorpay_enabled:
            raise PaymentError("Razorpay is not configured on this server")
        if not self._verify_signature(rzp_order_id, rzp_payment_id, signature):
            await self._orders.set_payment(
                order.id, method="razorpay", status="failed", ref=rzp_payment_id
            )
            raise PaymentError("Payment signature verification failed")
        return await self._orders.set_payment(
            order.id, method="razorpay", status="paid", ref=rzp_payment_id
        )

    async def confirm_demo(self, order: Order, outcome: str) -> Order:
        """Complete a demo payment. ``outcome`` is "success" or "fail"."""
        if self._settings.razorpay_enabled:
            raise PaymentError("Demo payments are disabled when Razorpay is configured")
        if outcome == "success":
            return await self._orders.set_payment(
                order.id, method="razorpay", status="paid", ref="demo_paid"
            )
        return await self._orders.set_payment(
            order.id, method="razorpay", status="failed", ref="demo_failed"
        )

    # ---- webhook (server-to-server, the reliable source of truth) ----

    @property
    def webhook_configured(self) -> bool:
        return bool(self._settings.razorpay_webhook_secret)

    def verify_webhook(self, raw_body: bytes, signature: str) -> bool:
        """Verify Razorpay's ``X-Razorpay-Signature`` over the raw request body."""
        secret = (self._settings.razorpay_webhook_secret or "").encode()
        expected = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature or "")

    async def handle_webhook_event(self, event: dict) -> str:
        """Apply a verified webhook event. Returns a short status for logging."""
        kind = event.get("event", "")
        entity = (
            event.get("payload", {}).get("payment", {}).get("entity", {})
            or event.get("payload", {}).get("order", {}).get("entity", {})
        )
        rzp_order_id = entity.get("order_id") or entity.get("id")
        if not rzp_order_id:
            return "ignored:no-order"

        order = await self._orders.find_by_gateway_order(rzp_order_id)
        if order is None:
            return "ignored:unknown-order"

        if kind in ("payment.captured", "order.paid"):
            if order.payment_status == "paid":
                return "noop:already-paid"
            payment_id = entity.get("id") if kind == "payment.captured" else order.payment_ref
            await self._orders.set_payment(
                order.id, method="razorpay", status="paid", ref=payment_id or "webhook"
            )
            return "applied:paid"
        if kind == "payment.failed" and order.payment_status != "paid":
            await self._orders.set_payment(
                order.id, method="razorpay", status="failed", ref=entity.get("id")
            )
            return "applied:failed"
        return f"ignored:{kind}"

    async def confirm_cash(self, order: Order) -> Order:
        """Place a cash order: payable at the counter, staff confirm collection."""
        return await self._orders.set_payment(
            order.id, method="cash", status="pending", ref=None
        )

    async def mark_cash_collected(self, order: Order) -> Order:
        return await self._orders.set_payment(
            order.id, method="cash", status="paid", ref="cash_collected"
        )
