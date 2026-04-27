"""Smoke test the FastAPI health endpoint via TestClient (no DB needed)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from geshtu.main import create_app


def test_health_returns_status():
    app = create_app()
    client = TestClient(app)
    r = client.get("/health")
    # Status may be "ok" or "degraded" depending on DB availability — both fine.
    assert r.status_code == 200
    body = r.json()
    assert body["version"]
    assert "db" in body
