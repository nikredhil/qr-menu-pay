def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_config_reports_demo_gateway(client):
    cfg = client.get("/config").json()
    assert cfg["app_name"] == "HSR Club Dine"
    assert cfg["payment_provider"] == "demo"  # forced in conftest
    assert cfg["otp_demo_mode"] is True


def test_security_headers_present(client):
    h = client.get("/health").headers
    assert h.get("X-Content-Type-Options") == "nosniff"
    assert h.get("X-Frame-Options") == "DENY"
    # HSTS only in prod
    assert "Strict-Transport-Security" not in h


def test_public_menu_lists_available_items(client, seeded):
    items = client.get("/menu").json()["items"]
    names = {i["name"] for i in items}
    assert {"Paneer Tikka", "Butter Chicken"} <= names


def test_menu_create_requires_admin(client):
    # No token → 401/403
    res = client.post("/menu", json={"name": "X", "price": 1, "category": "Starters"})
    assert res.status_code in (401, 403)


def test_hidden_items_excluded_from_public_menu(client, admin_headers, seeded):
    # Hide one item; it should drop from the public menu but stay in the admin list.
    client.patch(f"/menu/{seeded['item1']}", json={"available": False}, headers=admin_headers)
    public = {i["id"] for i in client.get("/menu").json()["items"]}
    assert seeded["item1"] not in public
    admin = {i["id"] for i in client.get("/menu?all_items=true").json()["items"]}
    assert seeded["item1"] in admin


def test_unknown_table_404(client):
    assert client.get("/tables/NOPE").status_code == 404
