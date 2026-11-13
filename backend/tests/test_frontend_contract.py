"""End-to-end API contract used by the React application, against real CSVs."""
from pathlib import Path

from backend.app import create_app


def test_frontend_workflow_contract_uses_real_archive_and_sqlite(tmp_path):
    root = Path(__file__).resolve().parents[2]
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "integration-test-secret-that-is-not-production",
        "DATABASE": str(tmp_path / "integration.sqlite3"),
        "DATA_DIR": str(root / "backend" / "data"),
        "FRONTEND_ORIGINS": ["http://localhost:5173"],
        "SESSION_COOKIE_SECURE": False,
    })
    client = app.test_client()

    csrf = client.get("/api/auth/csrf").get_json()["csrf_token"]
    registered = client.post("/api/auth/register", json={
        "name": "Integration Analyst", "email": "integration@example.com", "password": "secure-pass-123",
    }, headers={"X-CSRF-Token": csrf})
    assert registered.status_code == 201
    assert registered.get_json()["user"]["email"] == "integration@example.com"
    assert client.get("/api/auth/me").get_json()["user"]["id"] == registered.get_json()["user"]["id"]

    metadata = client.get("/api/metadata").get_json()
    assert metadata["historical"] is True
    assert metadata["date_range"]["start"] and metadata["date_range"]["end"]
    assert metadata["datasets"]["national"]["available"] is True

    dashboard = client.get("/api/national").get_json()
    assert dashboard["trend"] and dashboard["latest"]["Date"]
    start, end = dashboard["date_range"]["start"], dashboard["date_range"]["end"]
    filtered = client.get(f"/api/dashboard/trends?start={start}&end={end}&metric=Daily%20Confirmed").get_json()
    assert filtered["rows"]
    assert all(start <= row["Date"] <= end for row in filtered["rows"])

    state_comparison = client.get("/api/analytics/state-comparison?states=Karnataka,Maharashtra&metric=Confirmed").get_json()
    assert state_comparison["metric_type"] == "cumulative"
    assert state_comparison["rows"]
    testing = client.get(f"/api/analytics/testing?level=state&start={start}&end={end}").get_json()
    assert "regions" in testing and "positivity_method" in testing
    explorer = client.get("/api/data/explorer?dataset=national&limit=5&sort_by=Date&sort_order=asc").get_json()
    assert len(explorer["rows"]) == 5
    assert explorer["pagination"]["total"] >= 5
    insights = client.get(f"/api/insights?start={start}&end={end}").get_json()
    assert insights["historical"] is True
    assert insights["observation_count"] > 0

    csrf = client.get("/api/auth/csrf").get_json()["csrf_token"]
    assert client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 200
    assert client.get("/api/auth/me").get_json()["user"] is None

    csrf = client.get("/api/auth/csrf").get_json()["csrf_token"]
    logged_in = client.post("/api/auth/login", json={
        "email": "integration@example.com", "password": "secure-pass-123",
    }, headers={"X-CSRF-Token": csrf})
    assert logged_in.status_code == 200
    assert client.get("/api/auth/me").get_json()["user"]["email"] == "integration@example.com"
