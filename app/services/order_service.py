"""Order creation + lifecycle. Prices and totals are computed server-side from
the live menu so the client can never dictate what something costs."""
from __future__ import annotations

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
        self, repo: BaseRepository, menu_service: MenuService, table_service: TableService
    ) -> None:
        self._repo = repo
        self._menu = menu_service
        self._tables = table_service

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

    async def list(self, *, phone: str | None = None) -> list[Order]:
        filters = {"phone": phone} if phone else None
        docs = await self._repo.query(filters=filters, limit=1000)
        return [Order(**d) for d in docs]

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
        data = order.model_dump()
        data["status"] = status
        data["updated_at"] = _now()
        saved = await self._repo.update(data)
        return Order(**saved)

    async def set_payment(
        self, order_id: str, *, method: str, status: str, ref: str | None
    ) -> Order:
        order = await self.get(order_id)
        data = order.model_dump()
        data["payment_method"] = method
        data["payment_status"] = status
        data["payment_ref"] = ref
        data["updated_at"] = _now()
        saved = await self._repo.update(data)
        return Order(**saved)
