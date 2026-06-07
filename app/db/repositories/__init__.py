"""Container names + partition keys for every document type we persist."""
from __future__ import annotations

# (container name, partition-key field) for each document type.
CONTAINERS: tuple[tuple[str, str], ...] = (
    ("menu_items", "category"),
    ("tables", "id"),
    ("orders", "id"),
    ("customers", "id"),
)
