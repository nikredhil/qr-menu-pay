"""Request/response models for orders and their lifecycle."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# Kitchen/fulfilment lifecycle.
ORDER_STATUSES = ["placed", "preparing", "served", "cancelled"]
# Money lifecycle, tracked separately so a "cash" order can be placed unpaid.
PAYMENT_STATUSES = ["pending", "paid", "failed", "refunded"]
PAYMENT_METHODS = ["razorpay", "cash"]


class OrderItemInput(BaseModel):
    menu_item_id: str
    quantity: int = Field(ge=1, le=50)


class OrderCreate(BaseModel):
    table_id: str
    items: list[OrderItemInput] = Field(min_length=1)
    notes: str = Field(default="", max_length=400)


class OrderLine(BaseModel):
    menu_item_id: str
    name: str
    unit_price: float
    quantity: int
    veg: bool = True

    @property
    def line_total(self) -> float:
        return round(self.unit_price * self.quantity, 2)


class Order(BaseModel):
    id: str
    code: str                       # short human-friendly order number, e.g. "A23"
    table_id: str
    table_label: str
    outlet_id: str | None = None    # which outlet the order belongs to
    phone: str
    customer_name: str | None = None
    lines: list[OrderLine]
    subtotal: float
    tax: float
    total: float
    notes: str = ""
    status: Literal["placed", "preparing", "served", "cancelled"] = "placed"
    payment_method: Literal["razorpay", "cash"] | None = None
    payment_status: Literal["pending", "paid", "failed", "refunded"] = "pending"
    payment_ref: str | None = None  # razorpay_payment_id, or staff note for cash
    razorpay_order_id: str | None = None  # set at intent time; lets webhooks map back
    created_at: str
    updated_at: str


class OrderList(BaseModel):
    items: list[Order]


class OrderStatusUpdate(BaseModel):
    status: Literal["placed", "preparing", "served", "cancelled"]
