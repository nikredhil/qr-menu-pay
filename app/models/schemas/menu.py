"""Request/response models for the dining menu."""
from __future__ import annotations

from pydantic import BaseModel, Field

# Menu categories, in the order they should appear to a diner.
CATEGORIES = [
    "Starters",
    "Soups & Salads",
    "Main Course",
    "Breads & Rice",
    "Chinese",
    "Beverages",
    "Desserts",
]


class MenuItem(BaseModel):
    id: str
    name: str
    description: str = ""
    price: float
    category: str
    veg: bool = True
    available: bool = True
    image_url: str | None = None
    created_at: str | None = None


class MenuItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=400)
    price: float = Field(ge=0)
    category: str
    veg: bool = True
    available: bool = True
    image_url: str | None = None


class MenuItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=400)
    price: float | None = Field(default=None, ge=0)
    category: str | None = None
    veg: bool | None = None
    available: bool | None = None
    image_url: str | None = None


class MenuList(BaseModel):
    items: list[MenuItem]
    categories: list[str] = CATEGORIES
