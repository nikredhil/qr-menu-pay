"""Seed a handful of realistic *named* repeat diners (with visit history and
favourite dishes) so the staff dashboard's "Repeat diners" section looks
populated for a demo.

For each diner it writes:
  • a customer record (visits / points / total_spent / last_visit / member-since)
  • that many *served & paid* orders, drawn from their favourite dishes, spread
    over the time since they joined — so favourites, spend and revenue all
    compute from real orders (nothing is faked in the analytics layer).

Idempotent: customers are keyed by phone and orders by a stable id, so re-running
overwrites these demo records rather than duplicating them. Real data is left
untouched. Run with the venv active:

    python -m scripts.seed_demo_diners
"""
from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone

from app.core.config import get_settings
from app.db.repositories.file_store import JsonFileRepository

TAX_RATE = 0.05  # mirrors the server (GST on dining)

# (name, phone, member-since (days ago), visits, [favourite dishes])
DINERS: list[tuple[str, str, int, int, list[str]]] = [
    ("Priya Sharma", "9741100201", 160, 7,
     ["Paneer Butter Masala", "Masala Chaas", "Gulab Jamun (2 pc)"]),
    ("Arjun Mehta", "9741100202", 95, 5,
     ["Butter Chicken", "Chicken Dum Biryani", "Cold Coffee"]),
    ("Neha Reddy", "9741100203", 60, 4,
     ["Veg Hakka Noodles", "Gobi Manchurian", "Fresh Lime Soda"]),
    ("Rohan Nair", "9741100204", 42, 3,
     ["Mutton Rogan Josh", "Butter Naan", "Filter Coffee"]),
]

PAYMENT_ROTATION = ["razorpay", "razorpay", "cash"]


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


async def main() -> None:
    settings = get_settings()
    menu = json.load(open(os.path.join(settings.data_dir, "menu_items.json")))
    by_name = {m["name"]: m for m in menu.values()}
    tables = list(json.load(open(os.path.join(settings.data_dir, "tables.json"))).values())

    missing = [n for _, _, _, _, favs in DINERS for n in favs if n not in by_name]
    if missing:
        raise SystemExit(f"Menu is missing dishes referenced by the seed: {sorted(set(missing))}. "
                         f"Run `python -m scripts.seed_data` first.")

    cust_repo = JsonFileRepository(os.path.join(settings.data_dir, "customers.json"))
    order_repo = JsonFileRepository(os.path.join(settings.data_dir, "orders.json"))

    now = datetime.now(timezone.utc)
    made_orders = 0

    for di, (name, phone, member_days, visits, favs) in enumerate(DINERS):
        member_since = now - timedelta(days=member_days)
        # Spread this diner's visits evenly between just after they joined and
        # a couple of days ago.
        first = member_since + timedelta(days=2)
        last = now - timedelta(days=2, hours=di)  # a little jitter per diner
        span = max((last - first).total_seconds(), 1)

        total_spent = 0.0
        order_dates: list[datetime] = []

        for i in range(visits):
            frac = i / max(visits - 1, 1)
            placed = first + timedelta(seconds=span * frac)
            order_dates.append(placed)

            # Build 2 lines from their favourites so those dishes dominate.
            picks = [favs[i % len(favs)], favs[(i + 1) % len(favs)]]
            lines = []
            for j, dish in enumerate(picks):
                m = by_name[dish]
                qty = 2 if (i + j) % 2 == 0 else 1
                lines.append({
                    "menu_item_id": m["id"],
                    "name": m["name"],
                    "unit_price": float(m["price"]),
                    "quantity": qty,
                    "veg": bool(m["veg"]),
                    "notes": "",
                })
            subtotal = round(sum(l["unit_price"] * l["quantity"] for l in lines), 2)
            tax = round(subtotal * TAX_RATE, 2)
            total = round(subtotal + tax, 2)
            total_spent += total

            table = tables[(di + i) % len(tables)] if tables else {"id": "TABLE1", "label": "Table 1"}
            method = PAYMENT_ROTATION[i % len(PAYMENT_ROTATION)]
            await order_repo.create({
                "id": f"seed-{phone}-{i}",
                "code": f"{name[0]}{100 + di * 10 + i}",
                "table_id": table.get("id", "TABLE1"),
                "table_label": table.get("label", "Table 1"),
                "outlet_id": "default",
                "phone": phone,
                "customer_name": name,
                "lines": lines,
                "subtotal": subtotal,
                "tax": tax,
                "total": total,
                "notes": "",
                "status": "served",
                "payment_method": method,
                "payment_status": "paid",
                "payment_ref": "demo_paid" if method == "razorpay" else "cash",
                "razorpay_order_id": f"demo_order_{phone}_{i}" if method == "razorpay" else None,
                "created_at": _iso(placed),
                "updated_at": _iso(placed),
            })
            made_orders += 1

        total_spent = round(total_spent, 2)
        await cust_repo.create({
            "id": phone,
            "phone": phone,
            "name": name,
            "visits": visits,
            "points": round(total_spent * 0.1, 2),  # 10% loyalty, matching the app
            "total_spent": total_spent,
            "last_visit_at": _iso(max(order_dates)),
            "created_at": _iso(member_since),
        })
        print(f"  • {name} ({phone}): {visits} visits, ₹{total_spent:.0f} spent, favs {favs}")

    print(f"Seeded {len(DINERS)} named repeat diners and {made_orders} paid orders into {settings.data_dir}/")


if __name__ == "__main__":
    asyncio.run(main())
