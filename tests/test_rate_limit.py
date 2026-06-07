def test_otp_request_rate_limited(client):
    phone = "9123400001"
    # Default limit is 5 per window; the 6th should be throttled.
    codes = [client.post("/auth/otp/request", json={"phone": phone}).status_code for _ in range(5)]
    assert all(c == 200 for c in codes)
    blocked = client.post("/auth/otp/request", json={"phone": phone})
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


def test_admin_login_rate_limited(client):
    # Default limit is 8 per window; the 9th attempt should be throttled.
    for _ in range(8):
        client.post("/auth/admin/login", json={"password": "wrong"})
    blocked = client.post("/auth/admin/login", json={"password": "wrong"})
    assert blocked.status_code == 429
