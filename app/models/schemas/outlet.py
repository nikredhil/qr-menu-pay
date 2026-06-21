"""Outlets (branches). One backend can serve several restaurants/locations,
each with its own tables, menu, and orders. A diner only ever sees the outlet
their scanned table belongs to."""
from __future__ import annotations

from pydantic import BaseModel, Field


class Outlet(BaseModel):
    id: str
    name: str
    address: str = ""
    phone: str = ""
    active: bool = True
    created_at: str | None = None


class OutletCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    address: str = Field(default="", max_length=200)
    phone: str = Field(default="", max_length=20)


class OutletUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    address: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=20)
    active: bool | None = None


class OutletList(BaseModel):
    items: list[Outlet]
