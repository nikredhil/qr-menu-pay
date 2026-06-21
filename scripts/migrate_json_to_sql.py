"""One-time migration: copy data/*.json documents into the SQL database.

Run after provisioning Postgres (e.g. Neon) and setting DATABASE_URL. Idempotent
— it upserts by id, so re-running is safe and won't duplicate rows.

    DATABASE_URL=postgresql://... python -m scripts.migrate_json_to_sql

Reads every container's JSON file under DATA_DIR and writes its documents into
the matching SQL table. Orders created after the switch live only in SQL, so
this is mainly for carrying over seeded menu/tables and any existing orders.
"""
from __future__ import annotations

import asyncio
import json
import os

from app.core.config import get_settings
from app.db.repositories import CONTAINERS
from app.db.repositories.sql_store import create_sql_backends


async def main() -> None:
    settings = get_settings()
    if not settings.database_url:
        raise SystemExit("Set DATABASE_URL before running the migration.")

    engine, repos = await create_sql_backends(settings.database_url, CONTAINERS)
    total = 0
    try:
        for name, _pk in CONTAINERS:
            path = os.path.join(settings.data_dir, f"{name}.json")
            if not os.path.exists(path):
                print(f"{name}: no file, skipped")
                continue
            with open(path, encoding="utf-8") as fh:
                store = json.load(fh)
            if not isinstance(store, dict):
                print(f"{name}: unexpected format, skipped")
                continue
            for doc in store.values():
                await repos[name].create(doc)
            total += len(store)
            print(f"{name}: {len(store)} documents")
    finally:
        await engine.dispose()
    print(f"done — {total} documents migrated")


if __name__ == "__main__":
    asyncio.run(main())
