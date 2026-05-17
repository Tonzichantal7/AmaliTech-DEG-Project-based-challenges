import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.store import get_store

client = TestClient(app)


def setup_function():
    """Clear the store before each test."""
    get_store().clear()


# ── Register ──────────────────────────────────────────────────────────────────

def test_register_monitor_success():
    res = client.post("/monitors", json={"id": "dev-001", "timeout": 60, "alert_email": "admin@critmon.com"})
    assert res.status_code == 201
    data = res.json()
    assert data["id"] == "dev-001"
    assert data["status"] == "active"
    assert data["deadline"] is not None


def test_register_duplicate_monitor():
    client.post("/monitors", json={"id": "dev-dup", "timeout": 30, "alert_email": "a@b.com"})
    res = client.post("/monitors", json={"id": "dev-dup", "timeout": 30, "alert_email": "a@b.com"})
    assert res.status_code == 409


def test_register_invalid_email():
    res = client.post("/monitors", json={"id": "dev-bad", "timeout": 60, "alert_email": "not-an-email"})
    assert res.status_code == 422


def test_register_timeout_too_short():
    res = client.post("/monitors", json={"id": "dev-short", "timeout": 2, "alert_email": "a@b.com"})
    assert res.status_code == 422


# ── Heartbeat ─────────────────────────────────────────────────────────────────

def test_heartbeat_success():
    client.post("/monitors", json={"id": "dev-hb", "timeout": 60, "alert_email": "a@b.com"})
    res = client.post("/monitors/dev-hb/heartbeat")
    assert res.status_code == 200
    assert "reset" in res.json()["message"].lower()


def test_heartbeat_not_found():
    res = client.post("/monitors/ghost-device/heartbeat")
    assert res.status_code == 404


# ── Pause ─────────────────────────────────────────────────────────────────────

def test_pause_monitor():
    client.post("/monitors", json={"id": "dev-p", "timeout": 60, "alert_email": "a@b.com"})
    res = client.post("/monitors/dev-p/pause")
    assert res.status_code == 200
    monitor = client.get("/monitors/dev-p").json()
    assert monitor["status"] == "paused"
    assert monitor["deadline"] is None


def test_heartbeat_unpauses_monitor():
    client.post("/monitors", json={"id": "dev-unpause", "timeout": 60, "alert_email": "a@b.com"})
    client.post("/monitors/dev-unpause/pause")
    res = client.post("/monitors/dev-unpause/heartbeat")
    assert res.status_code == 200
    monitor = client.get("/monitors/dev-unpause").json()
    assert monitor["status"] == "active"


# ── List / Get / Delete ───────────────────────────────────────────────────────

def test_list_monitors():
    client.post("/monitors", json={"id": "dev-L1", "timeout": 60, "alert_email": "a@b.com"})
    client.post("/monitors", json={"id": "dev-L2", "timeout": 60, "alert_email": "b@b.com"})
    res = client.get("/monitors")
    assert res.status_code == 200
    ids = [m["id"] for m in res.json()]
    assert "dev-L1" in ids
    assert "dev-L2" in ids


def test_get_single_monitor():
    client.post("/monitors", json={"id": "dev-single", "timeout": 60, "alert_email": "a@b.com"})
    res = client.get("/monitors/dev-single")
    assert res.status_code == 200
    assert res.json()["id"] == "dev-single"


def test_delete_monitor():
    client.post("/monitors", json={"id": "dev-del", "timeout": 60, "alert_email": "a@b.com"})
    res = client.delete("/monitors/dev-del")
    assert res.status_code == 200
    assert client.get("/monitors/dev-del").status_code == 404
