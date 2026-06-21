"""Response models for the staff sales-analytics dashboard."""
from __future__ import annotations

from pydantic import BaseModel


class TopItem(BaseModel):
    menu_item_id: str
    name: str
    quantity: int
    revenue: float


class PeriodStats(BaseModel):
    orders: int            # orders placed in the period
    paid_orders: int       # of those, how many are paid
    revenue: float         # sum of paid order totals


class DashboardStats(BaseModel):
    today: PeriodStats
    all_time: PeriodStats
    # paid-order counts by method, e.g. {"razorpay": 12, "cash": 3}
    payment_mix: dict[str, int]
    # live kitchen counts by fulfilment status
    status_mix: dict[str, int]
    top_items: list[TopItem]
    average_rating: float
    feedback_count: int
    repeat_customers: int  # customers with 2+ paid visits
