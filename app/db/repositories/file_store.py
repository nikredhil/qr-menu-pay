"""JSON-file repository — durable local backend that survives restarts.

Mirrors :class:`InMemoryRepository`, but loads its document dict from a JSON
file on construction and re-serializes it to disk after every write.
"""
from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from app.db.repositories.base import BaseRepository


class JsonFileRepository(BaseRepository):
    def __init__(self, file_path: str) -> None:
        self._file_path = file_path
        self._lock = asyncio.Lock()
        self._store: dict[str, dict[str, Any]] = self._load()

    def _load(self) -> dict[str, dict[str, Any]]:
        if not os.path.exists(self._file_path):
            return {}
        try:
            with open(self._file_path, encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _flush(self) -> None:
        os.makedirs(os.path.dirname(self._file_path) or ".", exist_ok=True)
        tmp = f"{self._file_path}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self._store, fh, indent=2)
        os.replace(tmp, self._file_path)  # atomic on POSIX

    async def create(self, document: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            self._store[document["id"]] = dict(document)
            self._flush()
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
            self._flush()
            return dict(document)

    async def delete(self, item_id: str) -> bool:
        async with self._lock:
            if item_id not in self._store:
                return False
            del self._store[item_id]
            self._flush()
            return True
