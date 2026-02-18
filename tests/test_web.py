"""Tests for the FastAPI web dashboard."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.web import app, create_app


@pytest.fixture()
def vault(tmp_path):
    """Create a minimal vault structure for testing."""
    for folder in [
        "Inbox", "Needs_Action", "Plans", "Pending_Approval",
        "Approved", "Done", "Logs", "Incoming_Files", "Rejected",
        "In_Progress", "Updates",
    ]:
        (tmp_path / folder).mkdir()
    create_app(tmp_path)
    return tmp_path


@pytest.fixture()
def client(vault):
    """Return a TestClient for the FastAPI app."""
    return TestClient(app)


# --- Dashboard page tests ---

def test_dashboard_returns_200(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "AI Employee Dashboard" in resp.text


def test_dashboard_shows_idle_when_empty(client):
    resp = client.get("/")
    assert "Idle" in resp.text


def test_dashboard_shows_active_when_items_exist(client, vault):
    (vault / "Needs_Action" / "test-email.md").write_text("---\ntype: email\n---\n")
    resp = client.get("/")
    assert "Active" in resp.text


def test_dashboard_shows_folder_counts(client, vault):
    (vault / "Needs_Action" / "a.md").write_text("test")
    (vault / "Needs_Action" / "b.md").write_text("test")
    resp = client.get("/")
    assert "Needs_Action" in resp.text


def test_dashboard_shows_pending_approvals(client, vault):
    plan = vault / "Pending_Approval" / "plan-test.md"
    plan.write_text("---\nsource: email-test.md\nconfidence: 0.8\naction: reply\n---\nPlan content")
    resp = client.get("/")
    assert "plan-test.md" in resp.text
    assert "Approve" in resp.text
    assert "Reject" in resp.text


def test_dashboard_shows_no_pending_when_empty(client):
    resp = client.get("/")
    assert "No pending approvals" in resp.text


def test_dashboard_shows_needs_action_items(client, vault):
    (vault / "Needs_Action" / "email-urgent.md").write_text(
        "---\ntype: email\npriority: high\nsubject: Urgent request\n---\n"
    )
    resp = client.get("/")
    assert "Urgent request" in resp.text


def test_dashboard_shows_recent_activity(client, vault):
    log_entry = [{
        "timestamp": "2026-02-17T10:30:00Z",
        "actor": "orchestrator",
        "action": "email_sent",
        "source": "plan-test.md",
        "result": "reply_to:client@example.com",
    }]
    (vault / "Logs" / "2026-02-17.json").write_text(json.dumps(log_entry))
    resp = client.get("/")
    assert "email_sent" in resp.text


# --- API tests ---

def test_api_status_idle(client):
    resp = client.get("/api/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "idle"
    assert data["items_to_process"] == 0
    assert "Needs_Action" in data["folders"]


def test_api_status_active(client, vault):
    (vault / "Needs_Action" / "x.md").write_text("test")
    resp = client.get("/api/status")
    data = resp.json()
    assert data["status"] == "active"
    assert data["items_to_process"] >= 1


def test_api_pending_empty(client):
    resp = client.get("/api/pending")
    assert resp.status_code == 200
    assert resp.json()["approvals"] == []


def test_api_pending_with_items(client, vault):
    (vault / "Pending_Approval" / "plan-abc.md").write_text("---\nstatus: pending\n---\n")
    resp = client.get("/api/pending")
    data = resp.json()
    assert len(data["approvals"]) == 1


def test_api_activity_empty(client):
    resp = client.get("/api/activity")
    assert resp.status_code == 200
    assert resp.json()["activity"] == []


def test_api_activity_with_entries(client, vault):
    entries = [{"timestamp": "2026-02-17T10:00:00Z", "action": "test", "source": "x", "result": "ok"}]
    (vault / "Logs" / "2026-02-17.json").write_text(json.dumps(entries))
    resp = client.get("/api/activity")
    data = resp.json()
    assert len(data["activity"]) == 1


# --- Approve/Reject action tests ---

def test_approve_moves_file(client, vault):
    src = vault / "Pending_Approval" / "plan-test.md"
    src.write_text("---\nstatus: pending\n---\nPlan")
    resp = client.post("/approve/plan-test.md", follow_redirects=False)
    assert resp.status_code == 303
    assert not src.exists()
    assert (vault / "Approved" / "plan-test.md").exists()


def test_reject_moves_file(client, vault):
    src = vault / "Pending_Approval" / "plan-bad.md"
    src.write_text("---\nstatus: pending\n---\nBad plan")
    resp = client.post("/reject/plan-bad.md", follow_redirects=False)
    assert resp.status_code == 303
    assert not src.exists()
    assert (vault / "Rejected" / "plan-bad.md").exists()


def test_approve_nonexistent_returns_error(client):
    resp = client.post("/approve/no-such-file.md")
    assert "error" in resp.json()


def test_reject_nonexistent_returns_error(client):
    resp = client.post("/reject/no-such-file.md")
    assert "error" in resp.json()


def test_approve_creates_log_entry(client, vault):
    src = vault / "Pending_Approval" / "plan-log.md"
    src.write_text("test")
    client.post("/approve/plan-log.md", follow_redirects=False)
    # Check log was created
    log_files = list((vault / "Logs").glob("*.json"))
    assert len(log_files) >= 1
    entries = json.loads(log_files[0].read_text())
    assert any(e["action"] == "approved" for e in entries)


# --- View file tests ---

def test_view_file_returns_content(client, vault):
    (vault / "Needs_Action" / "test.md").write_text("# Test File\nHello world")
    resp = client.get("/view/Needs_Action/test.md")
    assert resp.status_code == 200
    assert "Hello world" in resp.text


def test_view_file_not_found(client):
    resp = client.get("/view/Needs_Action/nonexistent.md")
    assert resp.status_code == 404


# --- Health endpoint tests (Platinum tier) ---

def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["vault_exists"] is True
    assert "work_zone" in data
    assert "capabilities" in data


def test_api_status_includes_work_zone(client):
    resp = client.get("/api/status")
    data = resp.json()
    assert "work_zone" in data


def test_dashboard_shows_platinum_tier(client):
    resp = client.get("/")
    assert "Platinum Tier" in resp.text
