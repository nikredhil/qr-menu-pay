"""Seed the HSR Club dining menu and a set of tables.

Idempotent-ish: it writes fresh menu_items.json and tables.json under DATA_DIR,
replacing whatever's there. Run with the project venv active:

    python -m scripts.seed_data
"""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone

from app.core.config import get_settings
from app.db.repositories.file_store import JsonFileRepository

# (name, description, price ₹, category, veg)
MENU: list[tuple[str, str, float, str, bool]] = [
    # Starters
    ("Paneer Tikka", "Char-grilled cottage cheese, mint chutney", 320, "Starters", True),
    ("Hara Bhara Kabab", "Spinach & green pea patties", 280, "Starters", True),
    ("Chicken 65", "Spicy South-Indian fried chicken", 360, "Starters", False),
    ("Mutton Seekh Kabab", "Minced mutton skewers, tandoor-grilled", 420, "Starters", False),
    ("Crispy Corn", "Tossed with curry leaves & pepper", 260, "Starters", True),
    # Soups & Salads
    ("Cream of Tomato Soup", "Classic, served with croutons", 180, "Soups & Salads", True),
    ("Sweet Corn Chicken Soup", "Hearty and warming", 210, "Soups & Salads", False),
    ("Garden Green Salad", "Seasonal greens, house vinaigrette", 160, "Soups & Salads", True),
    # Main Course
    ("Paneer Butter Masala", "Cottage cheese in rich tomato gravy", 360, "Main Course", True),
    ("Dal Makhani", "Slow-cooked black lentils, butter & cream", 300, "Main Course", True),
    ("Butter Chicken", "Tandoori chicken in silky makhani gravy", 420, "Main Course", False),
    ("Mutton Rogan Josh", "Kashmiri-style mutton curry", 480, "Main Course", False),
    ("Kadai Veg", "Mixed vegetables in kadai masala", 320, "Main Course", True),
    # Breads & Rice
    ("Butter Naan", "Tandoor-baked, brushed with butter", 60, "Breads & Rice", True),
    ("Garlic Naan", "Naan with roasted garlic", 80, "Breads & Rice", True),
    ("Tandoori Roti", "Whole-wheat, tandoor-baked", 40, "Breads & Rice", True),
    ("Veg Dum Biryani", "Fragrant basmati, vegetables, raita", 320, "Breads & Rice", True),
    ("Chicken Dum Biryani", "Hyderabadi-style, served with raita", 380, "Breads & Rice", False),
    ("Jeera Rice", "Basmati tempered with cumin", 200, "Breads & Rice", True),
    # Chinese
    ("Veg Hakka Noodles", "Wok-tossed with vegetables", 260, "Chinese", True),
    ("Chicken Fried Rice", "Classic Indo-Chinese", 300, "Chinese", False),
    ("Gobi Manchurian", "Crispy cauliflower in Manchurian sauce", 280, "Chinese", True),
    ("Chilli Chicken", "Dry, with peppers & onions", 340, "Chinese", False),
    # Beverages
    ("Fresh Lime Soda", "Sweet / salted", 120, "Beverages", True),
    ("Masala Chaas", "Spiced buttermilk", 100, "Beverages", True),
    ("Cold Coffee", "Thick, with ice cream", 180, "Beverages", True),
    ("Filter Coffee", "South-Indian style", 90, "Beverages", True),
    ("Mineral Water (1L)", "Packaged drinking water", 50, "Beverages", True),
    # Desserts
    ("Gulab Jamun (2 pc)", "Warm, in sugar syrup", 140, "Desserts", True),
    ("Gajar Ka Halwa", "Carrot halwa with dry fruits", 180, "Desserts", True),
    ("Vanilla Ice Cream", "Two scoops", 130, "Desserts", True),
]

# (label, area, seats)
TABLES: list[tuple[str, str, int]] = [
    ("Table 1", "Main Dining", 4),
    ("Table 2", "Main Dining", 4),
    ("Table 3", "Main Dining", 2),
    ("Table 4", "Main Dining", 6),
    ("Table 5", "Garden", 4),
    ("Table 6", "Garden", 4),
    ("Table 7", "Bar", 2),
    ("Table 8", "Bar", 2),
    ("Banquet 1", "Banquet Hall", 10),
    ("Pool Deck 1", "Pool Deck", 4),
]

# A few sample translations (Hindi / Kannada) so the language switcher is
# demonstrable out of the box. Real menus would translate every item.
TRANSLATIONS: dict[str, dict] = {
    "Paneer Tikka": {"hi": {"name": "पनीर टिक्का"}, "kn": {"name": "ಪನೀರ್ ಟಿಕ್ಕಾ"}},
    "Butter Chicken": {"hi": {"name": "बटर चिकन"}, "kn": {"name": "ಬಟರ್ ಚಿಕನ್"}},
    "Masala Chaas": {"hi": {"name": "मसाला छाछ"}, "kn": {"name": "ಮಸಾಲಾ ಮಜ್ಜಿಗೆ"}},
    "Gulab Jamun (2 pc)": {"hi": {"name": "गुलाब जामुन"}, "kn": {"name": "ಗುಲಾಬ್ ಜಾಮೂನ್"}},
}

# Sample food photos (royalty-free Unsplash) for a few dishes to show the
# photo menu. Swap in your own URLs from the admin Menu screen.
IMAGES: dict[str, str] = {
    "Paneer Tikka": "https://images.unsplash.com/photo-1599487488170-d11ec9c172f0?w=400&q=70",
    "Butter Chicken": "https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?w=400&q=70",
    "Veg Dum Biryani": "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=400&q=70",
    "Cold Coffee": "https://images.unsplash.com/photo-1461023058943-07fcbe16d735?w=400&q=70",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(label: str) -> str:
    import re

    return re.sub(r"[^A-Za-z0-9]", "", label).upper() or "T"


async def main() -> None:
    settings = get_settings()
    os.makedirs(settings.data_dir, exist_ok=True)

    menu_repo = JsonFileRepository(os.path.join(settings.data_dir, "menu_items.json"))
    table_repo = JsonFileRepository(os.path.join(settings.data_dir, "tables.json"))

    outlet_repo = JsonFileRepository(os.path.join(settings.data_dir, "outlets.json"))
    await outlet_repo.create(
        {
            "id": "default",
            "name": settings.app_name,
            "address": "",
            "phone": "",
            "active": True,
            "created_at": _now(),
        }
    )

    for name, desc, price, category, veg in MENU:
        await menu_repo.create(
            {
                "id": str(uuid.uuid4()),
                "name": name,
                "description": desc,
                "price": float(price),
                "category": category,
                "veg": veg,
                "available": True,
                "image_url": IMAGES.get(name),
                "translations": TRANSLATIONS.get(name, {}),
                "outlet_id": "default",
                "created_at": _now(),
            }
        )

    for label, area, seats in TABLES:
        code = _slug(label)
        await table_repo.create(
            {
                "id": code,
                "label": label,
                "area": area,
                "seats": seats,
                "active": True,
                "outlet_id": "default",
                "created_at": _now(),
            }
        )

    print(f"Seeded {len(MENU)} menu items and {len(TABLES)} tables into {settings.data_dir}/")


if __name__ == "__main__":
    asyncio.run(main())
