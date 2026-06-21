"""Menu CRUD on top of a repository."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.db.repositories.base import BaseRepository
from app.models.schemas.menu import MenuItem, MenuItemCreate, MenuItemUpdate


class MenuItemNotFoundError(Exception):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MenuService:
    def __init__(self, repo: BaseRepository) -> None:
        self._repo = repo

    async def list(
        self, *, only_available: bool = False, outlet_id: str | None = None
    ) -> list[MenuItem]:
        docs = await self._repo.query(limit=1000)
        items = [MenuItem(**d) for d in docs]
        if only_available:
            items = [i for i in items if i.available]
        if outlet_id is not None:
            items = [i for i in items if (i.outlet_id or "default") == outlet_id]
        # Stable, diner-friendly ordering: by name within a category.
        items.sort(key=lambda i: (i.category, i.name.lower()))
        return items

    async def get(self, item_id: str) -> MenuItem:
        doc = await self._repo.get(item_id)
        if doc is None:
            raise MenuItemNotFoundError(item_id)
        return MenuItem(**doc)

    async def get_or_none(self, item_id: str) -> MenuItem | None:
        doc = await self._repo.get(item_id)
        return MenuItem(**doc) if doc is not None else None

    async def create(self, payload: MenuItemCreate) -> MenuItem:
        data = payload.model_dump()
        data["outlet_id"] = data.get("outlet_id") or "default"
        item = MenuItem(id=str(uuid.uuid4()), created_at=_now(), **data)
        await self._repo.create(item.model_dump())
        return item

    async def update(self, item_id: str, patch: MenuItemUpdate) -> MenuItem:
        doc = await self._repo.get(item_id)
        if doc is None:
            raise MenuItemNotFoundError(item_id)
        doc.update({k: v for k, v in patch.model_dump(exclude_unset=True).items()})
        saved = await self._repo.update(doc)
        return MenuItem(**saved)

    async def delete(self, item_id: str) -> None:
        if not await self._repo.delete(item_id):
            raise MenuItemNotFoundError(item_id)
