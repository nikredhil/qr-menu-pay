"""Request/response models for dining tables (each gets a scannable QR)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class Table(BaseModel):
    id: str          # short opaque code embedded in the QR, e.g. "T07"
    label: str       # human label shown to staff, e.g. "Table 7"
    area: str = ""   # optional zone, e.g. "Garden", "Banquet", "Bar"
    seats: int = 4
    active: bool = True
    outlet_id: str | None = None    # which outlet/branch this table belongs to
    created_at: str | None = None


class TableCreate(BaseModel):
    label: str = Field(min_length=1, max_length=60)
    area: str = Field(default="", max_length=60)
    seats: int = Field(default=4, ge=1, le=50)
    outlet_id: str | None = None


class TableList(BaseModel):
    items: list[Table]
