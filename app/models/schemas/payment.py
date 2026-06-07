"""Request/response models for the payment flow."""
from __future__ import annotations

from pydantic import BaseModel


class PaymentIntent(BaseModel):
    """What the frontend needs to open Razorpay Checkout (or the demo gateway)."""

    order_id: str            # our internal order id
    provider: str            # "razorpay" | "demo"
    razorpay_order_id: str
    key_id: str | None = None  # publishable key (null in demo mode)
    amount: int              # in paise (smallest currency unit)
    currency: str
    name: str
    description: str
    prefill_contact: str


class RazorpayVerify(BaseModel):
    order_id: str
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class DemoConfirm(BaseModel):
    order_id: str
    razorpay_order_id: str
    # "success" completes the order as paid; "fail" simulates a declined payment.
    outcome: str = "success"


class CashConfirm(BaseModel):
    order_id: str


class PaymentResult(BaseModel):
    order_id: str
    payment_status: str
    payment_method: str
    payment_ref: str | None = None
