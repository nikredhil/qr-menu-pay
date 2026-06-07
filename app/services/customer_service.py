"""Lightweight customer records, keyed by phone number."""
from __future__ import annotations

from datetime import datetime, timezone

from app.db.repositories.base import BaseRepository


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CustomerService:
    def __init__(self, repo: BaseRepository) -> None:
        self._repo = repo

    async def upsert(self, phone: str, name: str | None) -> dict:
        existing = await self._repo.get(phone)
        if existing is None:
            doc = {"id": phone, "phone": phone, "name": name, "created_at": _now()}
            return await self._repo.create(doc)
        # Keep the latest non-empty name they gave us.
        if name and name != existing.get("name"):
            existing["name"] = name
            return await self._repo.update(existing)
        return existing

    async def get(self, phone: str) -> dict | None:
        return await self._repo.get(phone)
