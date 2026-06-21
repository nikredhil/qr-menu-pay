"""Customer records, keyed by phone number, with simple loyalty tracking.

Beyond name/phone we keep a lightweight loyalty profile: how many paid visits a
diner has made, when they last visited, how much they've spent, and a running
points balance (earned per rupee spent). Staff can recognise regulars and run
basic rewards without a separate CRM.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.db.repositories.base import BaseRepository

# Loyalty points earned per rupee spent on a paid order.
POINTS_PER_RUPEE = 0.1  # ₹100 spent → 10 points


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CustomerService:
    def __init__(self, repo: BaseRepository) -> None:
        self._repo = repo

    @staticmethod
    def _with_loyalty_defaults(doc: dict) -> dict:
        """Backfill loyalty fields for records created before loyalty existed."""
        doc.setdefault("visits", 0)
        doc.setdefault("points", 0.0)
        doc.setdefault("total_spent", 0.0)
        doc.setdefault("last_visit_at", None)
        return doc

    async def upsert(self, phone: str, name: str | None) -> dict:
        existing = await self._repo.get(phone)
        if existing is None:
            doc = {
                "id": phone,
                "phone": phone,
                "name": name,
                "visits": 0,
                "points": 0.0,
                "total_spent": 0.0,
                "last_visit_at": None,
                "created_at": _now(),
            }
            return await self._repo.create(doc)
        existing = self._with_loyalty_defaults(existing)
        # Keep the latest non-empty name they gave us.
        if name and name != existing.get("name"):
            existing["name"] = name
            return await self._repo.update(existing)
        return existing

    async def get(self, phone: str) -> dict | None:
        doc = await self._repo.get(phone)
        return self._with_loyalty_defaults(doc) if doc is not None else None

    async def list(self) -> list[dict]:
        docs = await self._repo.query(limit=5000)
        return [self._with_loyalty_defaults(d) for d in docs]

    async def record_visit(self, phone: str, amount: float) -> dict:
        """Credit a paid visit: bump visit count, spend, points, last-visit time.

        Idempotency is the caller's responsibility — only call this on the
        transition into ``paid`` so a single order is counted once.
        """
        existing = await self._repo.get(phone)
        doc = self._with_loyalty_defaults(existing or {"id": phone, "phone": phone, "name": None, "created_at": _now()})
        doc["id"] = phone
        doc["phone"] = phone
        doc["visits"] = int(doc.get("visits", 0)) + 1
        doc["total_spent"] = round(float(doc.get("total_spent", 0.0)) + float(amount), 2)
        doc["points"] = round(float(doc.get("points", 0.0)) + float(amount) * POINTS_PER_RUPEE, 2)
        doc["last_visit_at"] = _now()
        return await (self._repo.update(doc) if existing else self._repo.create(doc))
