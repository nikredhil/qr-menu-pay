"""Outlet (branch) CRUD, plus a guaranteed default outlet.

The default outlet keeps single-venue deployments zero-config: tables and menu
items created without an explicit outlet are attached to it, so the multi-outlet
machinery is invisible until you actually add a second branch.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.db.repositories.base import BaseRepository
from app.models.schemas.outlet import Outlet, OutletCreate, OutletUpdate

DEFAULT_OUTLET_ID = "default"


class OutletNotFoundError(Exception):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class OutletService:
    def __init__(self, repo: BaseRepository, default_name: str) -> None:
        self._repo = repo
        self._default_name = default_name

    async def ensure_default(self) -> Outlet:
        """Create the default outlet once if it doesn't exist yet."""
        doc = await self._repo.get(DEFAULT_OUTLET_ID)
        if doc is not None:
            return Outlet(**doc)
        outlet = Outlet(id=DEFAULT_OUTLET_ID, name=self._default_name, created_at=_now())
        await self._repo.create(outlet.model_dump())
        return outlet

    async def list(self) -> list[Outlet]:
        docs = await self._repo.query(limit=1000)
        outlets = [Outlet(**d) for d in docs]
        outlets.sort(key=lambda o: (o.id != DEFAULT_OUTLET_ID, o.name.lower()))
        return outlets

    async def get(self, outlet_id: str) -> Outlet:
        doc = await self._repo.get(outlet_id)
        if doc is None:
            raise OutletNotFoundError(outlet_id)
        return Outlet(**doc)

    async def exists(self, outlet_id: str) -> bool:
        return await self._repo.get(outlet_id) is not None

    async def create(self, payload: OutletCreate) -> Outlet:
        outlet = Outlet(id=str(uuid.uuid4())[:8], created_at=_now(), **payload.model_dump())
        await self._repo.create(outlet.model_dump())
        return outlet

    async def update(self, outlet_id: str, patch: OutletUpdate) -> Outlet:
        doc = await self._repo.get(outlet_id)
        if doc is None:
            raise OutletNotFoundError(outlet_id)
        doc.update({k: v for k, v in patch.model_dump(exclude_unset=True).items()})
        saved = await self._repo.update(doc)
        return Outlet(**saved)

    async def delete(self, outlet_id: str) -> None:
        if outlet_id == DEFAULT_OUTLET_ID:
            raise OutletNotFoundError("The default outlet cannot be deleted")
        if not await self._repo.delete(outlet_id):
            raise OutletNotFoundError(outlet_id)
