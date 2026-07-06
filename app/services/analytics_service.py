"""Sales analytics for the staff dashboard.

Aggregates live data from the order, feedback, and customer stores. At a single
venue's volume an in-memory pass over orders is plenty; if this ever needs to
scale, the same shape can be served from pre-aggregated rollups.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from app.models.schemas.stats import DashboardStats, PeriodStats, RepeatDiner, TopItem
from app.services.customer_service import CustomerService
from app.services.feedback_service import FeedbackService
from app.services.order_service import OrderService


class AnalyticsService:
    def __init__(
        self,
        orders: OrderService,
        feedback: FeedbackService,
        customers: CustomerService,
    ) -> None:
        self._orders = orders
        self._feedback = feedback
        self._customers = customers

    @staticmethod
    def _today() -> str:
        return datetime.now(timezone.utc).date().isoformat()

    async def dashboard(self) -> DashboardStats:
        orders = await self._orders.list()
        today = self._today()

        def period(rows) -> PeriodStats:
            paid = [o for o in rows if o.payment_status == "paid"]
            return PeriodStats(
                orders=len(rows),
                paid_orders=len(paid),
                revenue=round(sum(o.total for o in paid), 2),
            )

        todays = [o for o in orders if (o.created_at or "")[:10] == today]

        payment_mix: dict[str, int] = defaultdict(int)
        status_mix: dict[str, int] = defaultdict(int)
        item_qty: dict[str, int] = defaultdict(int)
        item_rev: dict[str, float] = defaultdict(float)
        item_name: dict[str, str] = {}
        # per-diner dish tallies, to surface each repeat guest's favourites
        diner_items: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for o in orders:
            status_mix[o.status] += 1
            if o.payment_status == "paid":
                payment_mix[o.payment_method or "unknown"] += 1
                for line in o.lines:
                    item_qty[line.menu_item_id] += line.quantity
                    item_rev[line.menu_item_id] += line.line_total
                    item_name[line.menu_item_id] = line.name
                    if o.phone:
                        diner_items[o.phone][line.name] += line.quantity

        top_items = sorted(
            (
                TopItem(
                    menu_item_id=mid,
                    name=item_name.get(mid, "—"),
                    quantity=qty,
                    revenue=round(item_rev[mid], 2),
                )
                for mid, qty in item_qty.items()
            ),
            key=lambda t: t.quantity,
            reverse=True,
        )[:10]

        fb = await self._feedback.summary()
        customers = await self._customers.list()
        repeaters = [c for c in customers if int(c.get("visits", 0)) >= 2]
        repeaters.sort(
            key=lambda c: (int(c.get("visits", 0)), float(c.get("total_spent", 0))),
            reverse=True,
        )

        def favourites(phone: str) -> list[str]:
            tally = diner_items.get(phone, {})
            return [name for name, _ in sorted(tally.items(), key=lambda kv: kv[1], reverse=True)[:3]]

        repeat_diners = [
            RepeatDiner(
                phone=c["phone"],
                name=c.get("name"),
                visits=int(c.get("visits", 0)),
                total_spent=round(float(c.get("total_spent", 0)), 2),
                points=round(float(c.get("points", 0)), 2),
                last_visit_at=c.get("last_visit_at"),
                member_since=c.get("created_at"),
                favorite_items=favourites(c["phone"]),
            )
            for c in repeaters
        ]

        return DashboardStats(
            today=period(todays),
            all_time=period(orders),
            payment_mix=dict(payment_mix),
            status_mix=dict(status_mix),
            top_items=top_items,
            average_rating=fb.average_rating,
            feedback_count=fb.count,
            repeat_customers=len(repeaters),
            repeat_diners=repeat_diners,
        )
