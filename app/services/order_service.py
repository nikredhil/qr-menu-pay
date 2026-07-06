"""Order creation + lifecycle. Prices and totals are computed server-side from
the live menu so the client can never dictate what something costs."""
from __future__ import annotations

import asyncio
import secrets
import uuid
from datetime import datetime, timezone

from app.db.repositories.base import BaseRepository
from app.models.schemas.order import (
    Order,
    OrderCreate,
    OrderLine,
)
from app.services.menu_service import MenuService
from app.services.table_service import TableNotFoundError, TableService

# GST on restaurant dining in India is 5%. Adjust if your tax setup differs.
TAX_RATE = 0.05

_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no easily-confused chars


class OrderNotFoundError(Exception):
    pass


class OrderValidationError(Exception):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _order_code() -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(4))


class OrderService:
    def __init__(
        self,
        repo: BaseRepository,
        menu_service: MenuService,
        table_service: TableService,
        customer_service=None,
        notification_service=None,
    ) -> None:
        self._repo = repo
        self._menu = menu_service
        self._tables = table_service
        # Optional collaborators: loyalty + order notifications. Left as None in
        # unit tests that exercise ordering in isolation.
        self._customers = customer_service
        self._notifications = notification_service
        # Fire-and-forget notification tasks, kept referenced so the event loop
        # doesn't garbage-collect them mid-flight.
        self._bg_tasks: set[asyncio.Task] = set()

    def _fire(self, coro) -> None:
        """Run a best-effort side effect (an SMS send) off the request's path so
        a slow provider can't add latency to the order response during a rush.
        The coroutine already swallows its own errors."""
        task = asyncio.create_task(coro)
        self._bg_tasks.add(task)
        task.add_done_callback(self._bg_tasks.discard)

    async def create(self, payload: OrderCreate, phone: str, name: str | None) -> Order:
        try:
            table = await self._tables.get(payload.table_id)
        except TableNotFoundError as exc:
            raise OrderValidationError("Unknown or invalid table") from exc
        if not table.active:
            raise OrderValidationError("This table is not accepting orders")

        lines: list[OrderLine] = []
        for entry in payload.items:
            item = await self._menu.get_or_none(entry.menu_item_id)
            if item is None or not item.available:
                raise OrderValidationError("One of the items is no longer available")
            lines.append(
                OrderLine(
                    menu_item_id=item.id,
                    name=item.name,
                    unit_price=item.price,
                    quantity=entry.quantity,
                    veg=item.veg,
                    notes=entry.notes.strip(),
                )
            )

        subtotal = round(sum(line.line_total for line in lines), 2)
        tax = round(subtotal * TAX_RATE, 2)
        total = round(subtotal + tax, 2)
        now = _now()

        order = Order(
            id=str(uuid.uuid4()),
            code=_order_code(),
            table_id=table.id,
            table_label=table.label,
            outlet_id=table.outlet_id or "default",
            phone=phone,
            customer_name=name,
            lines=lines,
            subtotal=subtotal,
            tax=tax,
            total=total,
            notes=payload.notes,
            status="placed",
            payment_status="pending",
            created_at=now,
            updated_at=now,
        )
        await self._repo.create(order.model_dump())
        if self._notifications is not None:
            self._fire(
                self._notifications.order_placed(
                    phone=order.phone,
                    code=order.code,
                    table_label=order.table_label,
                    total=order.total,
                )
            )
        return order

    async def get(self, order_id: str) -> Order:
        doc = await self._repo.get(order_id)
        if doc is None:
            raise OrderNotFoundError(order_id)
        return Order(**doc)

    async def get_for_customer(self, order_id: str, phone: str) -> Order:
        order = await self.get(order_id)
        if order.phone != phone:
            raise OrderNotFoundError(order_id)
        return order

    async def list(
        self,
        *,
        phone: str | None = None,
        outlet_id: str | None = None,
        statuses: list[str] | None = None,
    ) -> list[Order]:
        filters = {"phone": phone} if phone else None
        docs = await self._repo.query(filters=filters, limit=1000)
        orders = [Order(**d) for d in docs]
        if outlet_id is not None:
            orders = [o for o in orders if (o.outlet_id or "default") == outlet_id]
        if statuses is not None:
            orders = [o for o in orders if o.status in statuses]
        return orders

    async def attach_gateway_order(self, order_id: str, razorpay_order_id: str) -> Order:
        """Record the Razorpay order id on our order so a webhook can map back."""
        order = await self.get(order_id)
        data = order.model_dump()
        data["razorpay_order_id"] = razorpay_order_id
        data["updated_at"] = _now()
        saved = await self._repo.update(data)
        return Order(**saved)

    async def find_by_gateway_order(self, razorpay_order_id: str) -> Order | None:
        """Reverse lookup used by the webhook (no index — fine at this scale)."""
        docs = await self._repo.query(
            filters={"razorpay_order_id": razorpay_order_id}, limit=1
        )
        return Order(**docs[0]) if docs else None

    async def set_status(self, order_id: str, status: str) -> Order:
        order = await self.get(order_id)
        was = order.status
        data = order.model_dump()
        data["status"] = status
        data["updated_at"] = _now()
        saved = await self._repo.update(data)
        updated = Order(**saved)
        # Notify the diner when their order is served (on the transition only).
        if status == "served" and was != "served" and self._notifications is not None:
            self._fire(
                self._notifications.order_served(
                    phone=updated.phone, code=updated.code, table_label=updated.table_label
                )
            )
        return updated

    async def set_payment(
        self, order_id: str, *, method: str, status: str, ref: str | None
    ) -> Order:
        order = await self.get(order_id)
        was_paid = order.payment_status == "paid"
        data = order.model_dump()
        data["payment_method"] = method
        data["payment_status"] = status
        data["payment_ref"] = ref
        data["updated_at"] = _now()
        saved = await self._repo.update(data)
        updated = Order(**saved)
        # Credit loyalty once, on the transition into paid.
        if status == "paid" and not was_paid and self._customers is not None:
            await self._customers.record_visit(updated.phone, updated.total)
        return updated
