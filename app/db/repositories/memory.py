"""In-memory repository — zero external dependencies, ephemeral."""
from __future__ import annotations

import asyncio
from typing import Any

from app.db.repositories.base import BaseRepository


class InMemoryRepository(BaseRepository):
    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def create(self, document: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            self._store[document["id"]] = dict(document)
            return dict(document)

    async def get(self, item_id: str) -> dict[str, Any] | None:
        doc = self._store.get(item_id)
        return dict(doc) if doc is not None else None

    async def query(
        self, filters: dict[str, Any] | None = None, limit: int = 200, offset: int = 0
    ) -> list[dict[str, Any]]:
        filters = filters or {}
        matches = [
            dict(doc)
            for doc in self._store.values()
            if all(doc.get(k) == v for k, v in filters.items())
        ]
        matches.sort(key=lambda d: d.get("created_at", ""), reverse=True)
        return matches[offset : offset + limit]

    async def update(self, document: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            self._store[document["id"]] = dict(document)
            return dict(document)

    async def delete(self, item_id: str) -> bool:
        async with self._lock:
            return self._store.pop(item_id, None) is not None
