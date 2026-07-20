"""Tests for GET /health."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_healthy():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"status": "healthy"}


def test_root_ok():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
