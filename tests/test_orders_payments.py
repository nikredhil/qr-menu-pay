from tests.conftest import customer_headers


def _place_order(client, seeded, headers, qty1=2, qty2=1):
    return client.post(
        "/orders",
        json={
            "table_id": seeded["table_id"],
            "items": [
                {"menu_item_id": seeded["item1"], "quantity": qty1},
                {"menu_item_id": seeded["item2"], "quantity": qty2},
            ],
            "notes": "less spicy",
        },
        headers=headers,
    )


def test_order_totals_computed_server_side(client, seeded):
    headers, _ = customer_headers(client)
    res = _place_order(client, seeded, headers)
    assert res.status_code == 201
    o = res.json()
    # 2*320 + 1*420 = 1060 subtotal, 5% GST = 53, total 1113
    assert o["subtotal"] == 1060
    assert o["tax"] == 53
    assert o["total"] == 1113
    assert o["status"] == "placed"
    assert o["payment_status"] == "pending"


def test_order_requires_customer_auth(client, seeded):
    res = _place_order(client, seeded, headers={})
    assert res.status_code in (401, 403)


def test_demo_payment_marks_paid(client, seeded):
    headers, _ = customer_headers(client)
    order = _place_order(client, seeded, headers).json()
    intent = client.post("/payments/intent", json={"order_id": order["id"]}, headers=headers).json()
    assert intent["provider"] == "demo"
    res = client.post(
        "/payments/demo/confirm",
        json={"order_id": order["id"], "razorpay_order_id": intent["razorpay_order_id"], "outcome": "success"},
        headers=headers,
    ).json()
    assert res["payment_status"] == "paid"


def test_cash_flow_and_admin_collect(client, seeded, admin_headers):
    headers, _ = customer_headers(client)
    order = _place_order(client, seeded, headers).json()
    cash = client.post("/payments/cash", json={"order_id": order["id"]}, headers=headers).json()
    assert cash["payment_method"] == "cash" and cash["payment_status"] == "pending"
    collected = client.post(f"/payments/{order['id']}/cash-collected", headers=admin_headers).json()
    assert collected["payment_status"] == "paid"


def test_customer_cannot_see_admin_board(client, seeded):
    headers, _ = customer_headers(client)
    assert client.get("/orders", headers=headers).status_code == 403


def test_customer_cannot_read_others_order(client, seeded):
    h1, _ = customer_headers(client, phone="9000000011")
    order = _place_order(client, seeded, h1).json()
    h2, _ = customer_headers(client, phone="9000000022")
    assert client.get(f"/orders/{order['id']}", headers=h2).status_code == 404


def test_price_cannot_be_dictated_by_client(client, seeded):
    # Even if the client sends a price field, the server ignores it (totals from menu).
    headers, _ = customer_headers(client)
    res = client.post(
        "/orders",
        json={
            "table_id": seeded["table_id"],
            "items": [{"menu_item_id": seeded["item1"], "quantity": 1, "unit_price": 1}],
        },
        headers=headers,
    )
    assert res.status_code == 201
    assert res.json()["subtotal"] == 320  # the real menu price, not the injected 1


def test_admin_can_advance_status(client, seeded, admin_headers):
    headers, _ = customer_headers(client)
    order = _place_order(client, seeded, headers).json()
    res = client.patch(f"/orders/{order['id']}/status", json={"status": "preparing"}, headers=admin_headers)
    assert res.status_code == 200 and res.json()["status"] == "preparing"
