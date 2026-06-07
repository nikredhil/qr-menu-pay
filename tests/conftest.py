"""Test config: isolate every test from real data, secrets, and the network.

Uses the in-memory backend, demo OTP, and an empty Razorpay config (so the demo
gateway is active — no calls to api.razorpay.com). A fresh app context per test
means fresh rate-limiters and an empty store, so tests don't bleed into each
other.
"""
from __future__ import annotations

import os

# Must be set before the app/settings are imported.
os.environ["DB_BACKEND"] = "memory"
os.environ["ENVIRONMENT"] = "local"
os.environ["OTP_DEMO_MODE"] = "true"
os.environ["ADMIN_PASSWORD"] = "test-admin"
os.environ["CORS_ORIGINS"] = "*"
# Force the demo payment gateway (override any .env Razorpay keys).
os.environ["RAZORPAY_KEY_ID"] = ""
os.environ["RAZORPAY_KEY_SECRET"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client():
    get_settings.cache_clear()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin_token(client):
    res = client.post("/auth/admin/login", json={"password": "test-admin"})
    assert res.status_code == 200
    return res.json()["access_token"]


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def seeded(client, admin_headers):
    """Create one table and two menu items; return their ids."""
    table = client.post(
        "/tables", json={"label": "Table 1", "area": "Main", "seats": 4}, headers=admin_headers
    ).json()
    item1 = client.post(
        "/menu",
        json={"name": "Paneer Tikka", "price": 320, "category": "Starters", "veg": True},
        headers=admin_headers,
    ).json()
    item2 = client.post(
        "/menu",
        json={"name": "Butter Chicken", "price": 420, "category": "Main Course", "veg": False},
        headers=admin_headers,
    ).json()
    return {"table_id": table["id"], "item1": item1["id"], "item2": item2["id"]}


def customer_headers(client, phone="9876500001", name="Tester"):
    """Run the OTP flow and return auth headers for a customer."""
    req = client.post("/auth/otp/request", json={"phone": phone, "name": name}).json()
    res = client.post("/auth/otp/verify", json={"phone": phone, "code": req["debug_otp"]}).json()
    return {"Authorization": f"Bearer {res['access_token']}"}, phone
