import sqlite3


def _register(client, csrf, email="analyst@example.com", password="secure-pass-123"):
    return client.post("/api/auth/register", json={"name": "Test Analyst", "email": email, "password": password}, headers=csrf)


def test_register_hashes_password_and_authenticates(client, csrf, app):
    response = _register(client, csrf)
    assert response.status_code == 201
    assert response.get_json()["user"]["email"] == "analyst@example.com"
    assert "password" not in response.get_json()["user"]
    with sqlite3.connect(app.config["DATABASE"]) as connection:
        password_hash = connection.execute("SELECT password_hash FROM users").fetchone()[0]
    assert password_hash != "secure-pass-123"
    assert password_hash.startswith("scrypt:") or password_hash.startswith("pbkdf2:")
    assert client.get("/api/auth/me").get_json()["user"]["name"] == "Test Analyst"


def test_registration_validation_and_unique_email(client, csrf):
    bad_email = client.post("/api/auth/register", json={"name": "Analyst", "email": "bad", "password": "secure-pass-123"}, headers=csrf)
    short_password = client.post("/api/auth/register", json={"name": "Analyst", "email": "a@example.com", "password": "short"}, headers=csrf)
    assert bad_email.status_code == 400
    assert short_password.status_code == 400
    assert _register(client, csrf).status_code == 201
    duplicate = _register(client, csrf, email="ANALYST@example.com")
    assert duplicate.status_code == 409


def test_login_and_logout(client, csrf, app):
    _register(client, csrf)
    stale_cookie = client.get_cookie(app.config.get("SESSION_COOKIE_NAME", "session")).value
    assert client.post("/api/auth/logout", headers=csrf).status_code == 200
    # A copied, still correctly signed Flask cookie must no longer authenticate.
    client.set_cookie(app.config.get("SESSION_COOKIE_NAME", "session"), stale_cookie)
    assert client.get("/api/auth/me").get_json()["user"] is None
    assert client.get("/api/auth/preferences").status_code == 401
    fresh_csrf = {"X-CSRF-Token": client.get("/api/auth/csrf").get_json()["csrf_token"]}
    invalid = client.post("/api/auth/login", json={"email": "analyst@example.com", "password": "wrong-pass"}, headers=fresh_csrf)
    assert invalid.status_code == 401
    valid = client.post("/api/auth/login", json={"email": "ANALYST@example.com", "password": "secure-pass-123"}, headers=fresh_csrf)
    assert valid.status_code == 200
    assert valid.get_json()["user"]["name"] == "Test Analyst"


def test_mutations_require_csrf_and_preferences_require_auth(client, csrf):
    blocked = client.post("/api/auth/register", json={"name": "Test", "email": "x@example.com", "password": "secure-pass-123"})
    assert blocked.status_code == 403
    unauthorized = client.get("/api/auth/preferences")
    assert unauthorized.status_code == 401
    _register(client, csrf)
    saved = client.put("/api/auth/preferences", json={"dateRange": {"start": "2020-01-30", "end": "2020-02-02"}}, headers=csrf)
    assert saved.status_code == 200
    assert client.get("/api/auth/preferences").get_json()["dateRange"]["start"] == "2020-01-30"


def test_expired_database_session_is_rejected(client, csrf, app):
    _register(client, csrf, email="expired@example.com")
    with sqlite3.connect(app.config["DATABASE"]) as connection:
        connection.execute("UPDATE auth_sessions SET expires_at='2000-01-01 00:00:00'")
        connection.commit()
    assert client.get("/api/auth/me").get_json()["user"] is None
    assert client.get("/api/auth/preferences").status_code == 401
