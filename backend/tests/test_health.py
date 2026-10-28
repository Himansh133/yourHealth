from fastapi.testclient import TestClient

from app.main import app


def test_live_returns_ok():
    client = TestClient(app)
    resp = client.get("/api/v1/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
