from tests.conftest import customer_headers


def test_otp_request_returns_demo_code(client):
    res = client.post("/auth/otp/request", json={"phone": "9876512345"}).json()
    assert len(res["debug_otp"]) == 6
    assert res["expires_in"] > 0


def test_otp_verify_issues_token(client):
    headers, phone = customer_headers(client, phone="9876512300")
    assert headers["Authorization"].startswith("Bearer ")


def test_otp_wrong_code_rejected(client):
    client.post("/auth/otp/request", json={"phone": "9876512301"})
    res = client.post("/auth/otp/verify", json={"phone": "9876512301", "code": "000000"})
    assert res.status_code == 400


def test_invalid_phone_rejected(client):
    res = client.post("/auth/otp/request", json={"phone": "12345"})
    assert res.status_code == 422


def test_phone_is_normalized(client):
    # +91 / spaces are stripped to a 10-digit number.
    res = client.post("/auth/otp/request", json={"phone": "+91 98765 12302"}).json()
    assert res["phone"] == "9876512302"


def test_admin_login_ok_and_bad(client):
    assert client.post("/auth/admin/login", json={"password": "test-admin"}).status_code == 200
    assert client.post("/auth/admin/login", json={"password": "nope"}).status_code == 401
