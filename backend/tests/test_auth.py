def test_register_returns_user_without_password(client):
    resp = client.post("/api/v1/auth/register", json={"email": "a@example.com", "password": "correct horse battery"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "a@example.com"
    assert "password" not in body and "password_hash" not in body


def test_register_duplicate_email_case_insensitive(client):
    client.post("/api/v1/auth/register", json={"email": "a@example.com", "password": "correct horse battery"})
    resp = client.post("/api/v1/auth/register", json={"email": "A@Example.com", "password": "correct horse battery"})
    assert resp.status_code == 409


def test_register_rejects_short_password(client):
    resp = client.post("/api/v1/auth/register", json={"email": "a@example.com", "password": "short"})
    assert resp.status_code == 422


def test_login_sets_httponly_cookie_and_me_works(client):
    client.post("/api/v1/auth/register", json={"email": "a@example.com", "password": "correct horse battery"})
    resp = client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "correct horse battery"})
    assert resp.status_code == 200
    assert "httponly" in resp.headers["set-cookie"].lower()

    me = client.get("/api/v1/me")
    assert me.status_code == 200
    assert me.json()["email"] == "a@example.com"


def test_login_wrong_password_401(client):
    client.post("/api/v1/auth/register", json={"email": "a@example.com", "password": "correct horse battery"})
    resp = client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "wrong password!!"})
    assert resp.status_code == 401


def test_login_unknown_email_401(client):
    resp = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "whatever123"})
    assert resp.status_code == 401


def test_me_without_cookie_401(client):
    assert client.get("/api/v1/me").status_code == 401


def test_me_with_tampered_cookie_401(client):
    client.cookies.set("session", "not-a-real-token")
    assert client.get("/api/v1/me").status_code == 401


def test_logout_clears_session(client):
    client.post("/api/v1/auth/register", json={"email": "a@example.com", "password": "correct horse battery"})
    client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "correct horse battery"})
    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.get("/api/v1/me").status_code == 401
