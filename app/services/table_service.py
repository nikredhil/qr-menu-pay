"""Table CRUD. Each table's id doubles as the opaque code embedded in its QR."""
from __future__ import annotations

import re
from datetime import datetime, timezone

from app.db.repositories.base import BaseRepository
from app.models.schemas.table import Table, TableCreate


class TableNotFoundError(Exception):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(label: str) -> str:
    """Derive a short uppercase code from a label, e.g. 'Table 7' -> 'TABLE7'."""
    return re.sub(r"[^A-Za-z0-9]", "", label).upper() or "T"


class TableService:
    def __init__(self, repo: BaseRepository) -> None:
        self._repo = repo

    async def list(self) -> list[Table]:
        docs = await self._repo.query(limit=1000)
        tables = [Table(**d) for d in docs]
        tables.sort(key=lambda t: t.label)
        return tables

    async def get(self, table_id: str) -> Table:
        doc = await self._repo.get(table_id)
        if doc is None:
            raise TableNotFoundError(table_id)
        return Table(**doc)

    async def create(self, payload: TableCreate) -> Table:
        # Build a unique, human-readable code from the label.
        base = _slug(payload.label)
        code, n = base, 1
        while await self._repo.get(code) is not None:
            n += 1
            code = f"{base}-{n}"
        table = Table(id=code, created_at=_now(), **payload.model_dump())
        await self._repo.create(table.model_dump())
        return table

    async def delete(self, table_id: str) -> None:
        if not await self._repo.delete(table_id):
            raise TableNotFoundError(table_id)
