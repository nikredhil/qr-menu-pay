"""Async SQL repository — Postgres backend for high-concurrency order writes.

Each document type maps to one table: an ``id`` primary key, an indexed
``created_at`` for ordering, and the full document in a ``data`` JSON column
(JSONB on Postgres). The few fields the services actually filter on
(``phone``, ``razorpay_order_id``, ``order_id``) get JSONB expression indexes
so the webhook reverse-lookup and "my orders" query don't scan the table.

Why this exists: :class:`JsonFileRepository` rewrites the *entire* file under a
single process-wide ``asyncio.Lock`` on every write, so concurrent orders
serialize and the cost grows with the file. Here writes are independent upserts
the database coordinates with row-level locks — a single async worker can keep
hundreds of orders in flight at once. See DEPLOY.md for the rationale.

Targets Postgres in production (Neon). The table shape is dialect-neutral so a
local SQLite URL works for a quick smoke test of create/get/delete; the JSONB
expression indexes and the JSON-path ``query`` filters are Postgres-only.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import Column, MetaData, String, Table, delete, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.types import JSON

from app.db.repositories.base import BaseRepository

# Document fields the services filter on (order_service / feedback_service).
# Indexed on Postgres so webhook + "my orders" lookups stay scan-free.
_INDEXED_KEYS = ("phone", "razorpay_order_id", "order_id")

# JSONB on Postgres (indexable, typed), plain JSON (TEXT) anywhere else.
_JSON = JSON().with_variant(JSONB(), "postgresql")


def _make_table(metadata: MetaData, container: str) -> Table:
    return Table(
        container,
        metadata,
        Column("id", String, primary_key=True),
        Column("created_at", String, index=True),
        Column("data", _JSON, nullable=False),
    )


class SqlRepository(BaseRepository):
    """One document container backed by a single SQL table. Shares the engine's
    connection pool with every other container via ``sessionmaker``."""

    def __init__(
        self, sessionmaker: async_sessionmaker, table: Table, *, is_postgres: bool = True
    ) -> None:
        self._sm = sessionmaker
        self._table = table
        self._is_postgres = is_postgres

    # create and update are both upserts: this matches the dict-set semantics of
    # the in-memory / JSON backends (writing an id always wins, present or not).
    async def create(self, document: dict[str, Any]) -> dict[str, Any]:
        return await self._upsert(document)

    async def update(self, document: dict[str, Any]) -> dict[str, Any]:
        return await self._upsert(document)

    async def _upsert(self, document: dict[str, Any]) -> dict[str, Any]:
        doc = dict(document)
        values = {"id": doc["id"], "created_at": doc.get("created_at"), "data": doc}
        stmt = pg_insert(self._table).values(**values).on_conflict_do_update(
            index_elements=[self._table.c.id],
            set_={"created_at": values["created_at"], "data": doc},
        )
        async with self._sm() as session:
            await session.execute(stmt)
            await session.commit()
        return doc

    async def get(self, item_id: str) -> dict[str, Any] | None:
        stmt = select(self._table.c.data).where(self._table.c.id == item_id)
        async with self._sm() as session:
            row = (await session.execute(stmt)).first()
        return dict(row[0]) if row else None

    async def query(
        self, filters: dict[str, Any] | None = None, limit: int = 200, offset: int = 0
    ) -> list[dict[str, Any]]:
        stmt = select(self._table.c.data)
        for key, value in (filters or {}).items():
            element = self._table.c.data[key]
            # JSON-path equality. On Postgres ``.astext`` (-> ``data->>'key'``)
            # matches the expression index; SQLite needs the portable cast.
            expr = element.astext if self._is_postgres else element.as_string()
            stmt = stmt.where(expr == str(value))
        stmt = (
            stmt.order_by(self._table.c.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        async with self._sm() as session:
            rows = (await session.execute(stmt)).all()
        return [dict(r[0]) for r in rows]

    async def delete(self, item_id: str) -> bool:
        stmt = delete(self._table).where(self._table.c.id == item_id)
        async with self._sm() as session:
            result = await session.execute(stmt)
            await session.commit()
        return bool(result.rowcount)


def _normalize_url(url: str) -> tuple[str, dict[str, Any]]:
    """Turn a libpq-style URL (what Neon/Render hand out) into an async DSN plus
    asyncpg connect args. asyncpg doesn't understand ``sslmode`` in the DSN, so
    we translate it to its ``ssl`` flag and drop params it can't parse."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]

    connect_args: dict[str, Any] = {}
    if url.startswith("postgresql+asyncpg://"):
        parts = urlsplit(url)
        query = dict(parse_qsl(parts.query))
        sslmode = query.pop("sslmode", None)
        query.pop("channel_binding", None)  # asyncpg rejects it in the DSN
        url = urlunsplit(
            (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
        )
        if (sslmode or "require") != "disable":
            connect_args["ssl"] = True  # Neon requires TLS
        # Behind Neon's pgbouncer pooler, asyncpg's prepared-statement cache
        # breaks across pooled connections — disable it.
        connect_args["statement_cache_size"] = 0
    return url, connect_args


def _build_engine(database_url: str, *, echo: bool = False) -> AsyncEngine:
    url, connect_args = _normalize_url(database_url)
    kwargs: dict[str, Any] = {"echo": echo, "connect_args": connect_args}
    if url.startswith("postgresql+asyncpg://"):
        # Pool tuning is Postgres-only; SQLite (smoke tests) uses NullPool and
        # rejects these args.
        kwargs.update(
            pool_pre_ping=True,  # survive Neon scale-to-zero cold starts
            pool_size=5,
            max_overflow=5,
        )
    return create_async_engine(url, **kwargs)


async def create_sql_backends(
    database_url: str, containers: tuple[tuple[str, str], ...]
) -> tuple[AsyncEngine, dict[str, SqlRepository]]:
    """Build the engine, create the per-container tables + indexes, and return a
    repository for each container. Idempotent — safe to run on every boot."""
    engine = _build_engine(database_url)
    metadata = MetaData()
    tables = {name: _make_table(metadata, name) for name, _pk in containers}

    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
        if engine.dialect.name == "postgresql":
            for name in tables:
                for key in _INDEXED_KEYS:
                    await conn.exec_driver_sql(
                        f'CREATE INDEX IF NOT EXISTS "ix_{name}_{key}" '
                        f"ON \"{name}\" ((data->>'{key}'))"
                    )

    is_postgres = engine.dialect.name == "postgresql"
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    repos = {
        name: SqlRepository(sessionmaker, tables[name], is_postgres=is_postgres)
        for name, _pk in containers
    }
    return engine, repos
