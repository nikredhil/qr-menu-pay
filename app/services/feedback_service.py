"""Guest feedback: create one rating per order, list + summarise for staff."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.db.repositories.base import BaseRepository
from app.models.schemas.feedback import Feedback, FeedbackCreate, FeedbackSummary
from app.models.schemas.order import Order


class FeedbackError(Exception):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _avg(values: list[int]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


class FeedbackService:
    def __init__(self, repo: BaseRepository) -> None:
        self._repo = repo

    async def for_order(self, order_id: str) -> Feedback | None:
        docs = await self._repo.query(filters={"order_id": order_id}, limit=1)
        return Feedback(**docs[0]) if docs else None

    async def create(self, payload: FeedbackCreate, order: Order) -> Feedback:
        """Record feedback for one of the caller's own orders (once)."""
        if await self.for_order(order.id) is not None:
            raise FeedbackError("Feedback already submitted for this order")
        fb = Feedback(
            id=str(uuid.uuid4()),
            order_id=order.id,
            order_code=order.code,
            table_label=order.table_label,
            phone=order.phone,
            customer_name=order.customer_name,
            rating=payload.rating,
            food_rating=payload.food_rating,
            service_rating=payload.service_rating,
            comment=payload.comment.strip(),
            created_at=_now(),
        )
        await self._repo.create(fb.model_dump())
        return fb

    async def list(self) -> list[Feedback]:
        docs = await self._repo.query(limit=5000)
        return [Feedback(**d) for d in docs]

    async def summary(self) -> FeedbackSummary:
        items = await self.list()
        return FeedbackSummary(
            count=len(items),
            average_rating=_avg([i.rating for i in items]) or 0.0,
            average_food=_avg([i.food_rating for i in items if i.food_rating]),
            average_service=_avg([i.service_rating for i in items if i.service_rating]),
        )
