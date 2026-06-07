"""Abstract repository interface shared by all storage backends."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseRepository(ABC):
    """CRUD contract for a single document type / container.

    Documents are plain dicts with at least an ``id`` field and a partition-key
    field. Concrete backends (in-memory, JSON file) implement the storage.
    """

    @abstractmethod
    async def create(self, document: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    async def get(self, item_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    async def query(
        self, filters: dict[str, Any] | None = None, limit: int = 200, offset: int = 0
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def update(self, document: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    async def delete(self, item_id: str) -> bool: ...
