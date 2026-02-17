"""Tests for the Email MCP Server tools."""
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# We test the tool functions directly (not via MCP protocol)
import mcp_servers.email_server as email_server


@pytest.fixture(autouse=True)
def set_vault_path(tmp_path):
    """Override vault path for all tests."""
    for folder in [
        "Inbox", "Needs_Action", "Plans", "Pending_Approval",
        "Approved", "Done", "Logs", "Incoming_Files", "Rejected",
    ]:
        (tmp_path / folder).mkdir()
    email_server.VAULT_PATH = tmp_path
    yield tmp_path


# --- get_vault_status tests ---

def test_get_vault_status_empty(set_vault_path):
    result = json.loads(email_server.get_vault_status())
    assert result["success"] is True
    assert result["status"] == "idle"
    assert result["items_to_process"] == 0


def test_get_vault_status_with_items(set_vault_path):
    (set_vault_path / "Needs_Action" / "test.md").write_text("test")
    (set_vault_path / "Pending_Approval" / "plan.md").write_text("test")
    result = json.loads(email_server.get_vault_status())
    assert result["success"] is True
    assert result["status"] == "active"
    assert result["items_to_process"] == 2
    assert result["folders"]["Needs_Action"] == 1
    assert result["folders"]["Pending_Approval"] == 1


# --- list_pending tests ---

def test_list_pending_empty(set_vault_path):
    result = json.loads(email_server.list_pending())
    assert result["success"] is True
    assert result["count"] == 0
    assert result["pending"] == []


def test_list_pending_with_items(set_vault_path):
    plan = set_vault_path / "Pending_Approval" / "plan-test.md"
    plan.write_text("---\nsource: email-test.md\nconfidence: 0.8\naction: reply\n---\nContent")
    result = json.loads(email_server.list_pending())
    assert result["success"] is True
    assert result["count"] == 1
    assert result["pending"][0]["filename"] == "plan-test.md"
    assert result["pending"][0]["confidence"] == 0.8


# --- send_email tests ---

def test_send_email_respects_daily_limit(set_vault_path):
    """When daily limit is reached, send_email should fail."""
    email_server.DAILY_SEND_LIMIT = 0  # Zero limit = always exceeded
    result = json.loads(email_server.send_email(
        gmail_id="abc123", to="test@example.com",
        subject="Test", body="Hello",
    ))
    assert result["success"] is False
    assert "limit" in result["error"].lower()
    email_server.DAILY_SEND_LIMIT = 20  # Reset


@patch("mcp_servers.email_server._get_gmail_service")
def test_send_email_success(mock_gmail, set_vault_path):
    """Successful send should return success and log action."""
    mock_service = MagicMock()
    mock_gmail.return_value = mock_service
    mock_service.users.return_value.messages.return_value.get.return_value.execute.return_value = {
        "payload": {"headers": [{"name": "Message-Id", "value": "<test@gmail.com>"}]},
        "threadId": "thread123",
    }
    mock_service.users.return_value.messages.return_value.send.return_value.execute.return_value = {
        "id": "sent123"
    }

    result = json.loads(email_server.send_email(
        gmail_id="abc123", to="test@example.com",
        subject="Re: Test", body="Hello there",
    ))
    assert result["success"] is True
    assert "test@example.com" in result["message"]


@patch("mcp_servers.email_server._get_gmail_service")
def test_send_email_logs_action(mock_gmail, set_vault_path):
    """Send should create a log entry."""
    mock_service = MagicMock()
    mock_gmail.return_value = mock_service
    mock_service.users.return_value.messages.return_value.get.return_value.execute.return_value = {
        "payload": {"headers": [{"name": "Message-Id", "value": "<test@gmail.com>"}]},
        "threadId": "thread123",
    }
    mock_service.users.return_value.messages.return_value.send.return_value.execute.return_value = {
        "id": "sent123"
    }

    email_server.send_email(
        gmail_id="abc123", to="test@example.com",
        subject="Re: Test", body="Hello",
    )

    # Filter out .send_count_* files — only look at date-based log files
    log_files = [f for f in (set_vault_path / "Logs").glob("*.json")
                 if not f.name.startswith(".send_count")]
    assert len(log_files) >= 1
    entries = json.loads(log_files[0].read_text())
    assert any(e["action"] == "email_sent" for e in entries)


@patch("mcp_servers.email_server._get_gmail_service")
def test_send_email_failure(mock_gmail, set_vault_path):
    """Failed send should return error."""
    mock_gmail.side_effect = Exception("Auth failed")
    result = json.loads(email_server.send_email(
        gmail_id="abc123", to="test@example.com",
        subject="Test", body="Hello",
    ))
    assert result["success"] is False
    assert "Auth failed" in result["error"]


# --- search_emails tests ---

@patch("mcp_servers.email_server._get_gmail_service")
def test_search_emails_success(mock_gmail, set_vault_path):
    """Search should return formatted email list."""
    mock_service = MagicMock()
    mock_gmail.return_value = mock_service
    mock_service.users.return_value.messages.return_value.list.return_value.execute.return_value = {
        "messages": [{"id": "msg1"}]
    }
    mock_service.users.return_value.messages.return_value.get.return_value.execute.return_value = {
        "payload": {"headers": [
            {"name": "From", "value": "sender@test.com"},
            {"name": "Subject", "value": "Hello"},
            {"name": "Date", "value": "Mon, 17 Feb 2026"},
        ]},
        "snippet": "Test email body",
    }

    result = json.loads(email_server.search_emails(query="is:unread", max_results=5))
    assert result["success"] is True
    assert result["count"] == 1
    assert result["emails"][0]["from"] == "sender@test.com"


@patch("mcp_servers.email_server._get_gmail_service")
def test_search_emails_error(mock_gmail, set_vault_path):
    """Search failure should return error."""
    mock_gmail.side_effect = Exception("API error")
    result = json.loads(email_server.search_emails(query="test"))
    assert result["success"] is False
