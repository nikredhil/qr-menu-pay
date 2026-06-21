"""End-to-end tests for the mydigimenu-style features: feedback, loyalty,
analytics, outlets, and the multi-language menu."""
from tests.conftest import customer_headers


def _place_and_pay(client, seeded, headers):
    order = client.post(
        "/orders",
        json={"table_id": seeded["table_id"], "items": [{"menu_item_id": seeded["item1"], "quantity": 2}]},
        headers=headers,
    ).json()
    intent = client.post("/payments/intent", json={"order_id": order["id"]}, headers=headers).json()
    client.post(
        "/payments/demo/confirm",
        json={"order_id": order["id"], "razorpay_order_id": intent["razorpay_order_id"], "outcome": "success"},
        headers=headers,
    )
    return order


# ---- feedback ----

def test_feedback_create_list_and_dedupe(client, seeded, admin_headers):
    headers, _ = customer_headers(client)
    order = _place_and_pay(client, seeded, headers)
    res = client.post(
        "/feedback",
        json={"order_id": order["id"], "rating": 5, "food_rating": 5, "service_rating": 4, "comment": "Lovely"},
        headers=headers,
    )
    assert res.status_code == 201 and res.json()["rating"] == 5
    # Second submission for the same order is rejected.
    dup = client.post("/feedback", json={"order_id": order["id"], "rating": 1}, headers=headers)
    assert dup.status_code == 409
    # Admin sees it; summary reflects it.
    items = client.get("/feedback", headers=admin_headers).json()["items"]
    assert len(items) == 1
    summary = client.get("/feedback/summary", headers=admin_headers).json()
    assert summary["count"] == 1 and summary["average_rating"] == 5.0


def test_feedback_requires_own_order(client, seeded):
    h1, _ = customer_headers(client, phone="9000001111")
    order = _place_and_pay(client, seeded, h1)
    h2, _ = customer_headers(client, phone="9000002222")
    res = client.post("/feedback", json={"order_id": order["id"], "rating": 5}, headers=h2)
    assert res.status_code == 404


# ---- loyalty ----

def test_loyalty_accrues_on_paid_visits(client, seeded, admin_headers):
    headers, phone = customer_headers(client, phone="9000003333")
    _place_and_pay(client, seeded, headers)
    _place_and_pay(client, seeded, headers)
    stats = client.get("/stats", headers=admin_headers).json()
    # Two paid visits by the same phone → counts as a repeat customer.
    assert stats["repeat_customers"] >= 1


# ---- analytics ----

def test_stats_dashboard_shape(client, seeded, admin_headers):
    headers, _ = customer_headers(client)
    _place_and_pay(client, seeded, headers)
    stats = client.get("/stats", headers=admin_headers).json()
    assert stats["today"]["paid_orders"] >= 1
    assert stats["all_time"]["revenue"] > 0
    assert stats["payment_mix"].get("razorpay", 0) >= 1
    assert stats["top_items"] and stats["top_items"][0]["quantity"] >= 2


def test_stats_requires_admin(client):
    assert client.get("/stats").status_code in (401, 403)


# ---- outlets ----

def test_default_outlet_exists_and_scopes_menu(client, seeded):
    outlets = client.get("/outlets").json()["items"]
    assert any(o["id"] == "default" for o in outlets)
    # Seeded menu items are attached to the default outlet.
    scoped = client.get("/menu?outlet=default").json()["items"]
    assert len(scoped) >= 1
    # An unknown outlet yields an empty menu.
    assert client.get("/menu?outlet=nope").json()["items"] == []


def test_admin_can_create_outlet(client, admin_headers):
    res = client.post("/outlets", json={"name": "HSR Club — Pool Bar"}, headers=admin_headers)
    assert res.status_code == 201 and res.json()["name"] == "HSR Club — Pool Bar"


# ---- multi-language ----

def test_menu_item_carries_translations(client, admin_headers):
    res = client.post(
        "/menu",
        json={
            "name": "Masala Dosa",
            "price": 120,
            "category": "Starters",
            "veg": True,
            "translations": {"hi": {"name": "मसाला डोसा"}},
        },
        headers=admin_headers,
    )
    assert res.status_code == 201
    assert res.json()["translations"]["hi"]["name"] == "मसाला डोसा"
