import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


@pytest.fixture
def mock_gmail_service():
    service = MagicMock()
    return service


@pytest.fixture
def vault(tmp_path):
    (tmp_path / "Needs_Action").mkdir()
    (tmp_path / "Logs").mkdir()
    return tmp_path


def test_gmail_watcher_check_for_updates_returns_messages(vault, mock_gmail_service):
    from src.watchers.gmail_watcher import GmailWatcher
    mock_gmail_service.users().messages().list.return_value.execute.return_value = {
        "messages": [{"id": "msg_1", "threadId": "t1"}]
    }
    mock_gmail_service.users().messages().get.return_value.execute.return_value = {
        "id": "msg_1",
        "payload": {
            "headers": [
                {"name": "From", "value": "sender@test.com"},
                {"name": "Subject", "value": "Test Email"},
                {"name": "Date", "value": "Mon, 16 Feb 2026 10:00:00 +0000"},
            ],
            "body": {"data": "SGVsbG8gV29ybGQ="},
        },
        "labelIds": ["INBOX", "UNREAD"],
    }
    watcher = GmailWatcher(vault_path=vault, gmail_service=mock_gmail_service, gmail_filter="is:unread")
    messages = watcher.check_for_updates()
    assert len(messages) == 1
    assert messages[0]["id"] == "msg_1"
    assert messages[0]["from"] == "sender@test.com"
    assert messages[0]["subject"] == "Test Email"


def test_gmail_watcher_check_no_messages(vault, mock_gmail_service):
    from src.watchers.gmail_watcher import GmailWatcher
    mock_gmail_service.users().messages().list.return_value.execute.return_value = {}
    watcher = GmailWatcher(vault_path=vault, gmail_service=mock_gmail_service)
    messages = watcher.check_for_updates()
    assert messages == []


def test_gmail_watcher_creates_action_file(vault, mock_gmail_service):
    from src.watchers.gmail_watcher import GmailWatcher
    watcher = GmailWatcher(vault_path=vault, gmail_service=mock_gmail_service)
    item = {
        "id": "msg_123",
        "from": "bob@example.com",
        "subject": "Invoice #42",
        "date": "2026-02-16T10:30:00Z",
        "body": "Please find attached the invoice.",
        "labels": ["INBOX", "IMPORTANT"],
    }
    path = watcher.create_action_file(item)
    assert path.exists()
    content = path.read_text()
    assert "type: email" in content
    assert "from: bob@example.com" in content
    assert "Invoice #42" in content
    assert "Please find attached the invoice." in content


def test_gmail_watcher_marks_as_processed(vault, mock_gmail_service):
    from src.watchers.gmail_watcher import GmailWatcher
    mock_gmail_service.users().labels().list.return_value.execute.return_value = {
        "labels": [{"id": "Label_123", "name": "Processed-by-FTE"}]
    }
    watcher = GmailWatcher(vault_path=vault, gmail_service=mock_gmail_service)
    watcher.mark_as_processed("msg_123")
    mock_gmail_service.users().messages().modify.assert_called_once()


def test_gmail_watcher_accepts_vip_senders(vault, mock_gmail_service):
    """GmailWatcher should accept and store vip_senders parameter."""
    from src.watchers.gmail_watcher import GmailWatcher
    watcher = GmailWatcher(
        vault_path=vault, gmail_service=mock_gmail_service,
        vip_senders=["boss@co.com"],
    )
    assert watcher.vip_senders == ["boss@co.com"]


def test_gmail_watcher_vip_senders_default_empty(vault, mock_gmail_service):
    """GmailWatcher should default vip_senders to empty list."""
    from src.watchers.gmail_watcher import GmailWatcher
    watcher = GmailWatcher(vault_path=vault, gmail_service=mock_gmail_service)
    assert watcher.vip_senders == []


def test_action_file_has_high_priority_for_urgent_email(vault, mock_gmail_service):
    """Action file should have priority: high when subject contains urgency keyword."""
    from src.watchers.gmail_watcher import GmailWatcher
    watcher = GmailWatcher(vault_path=vault, gmail_service=mock_gmail_service)
    item = {
        "id": "msg_urg",
        "from": "someone@example.com",
        "subject": "URGENT: Server is down",
        "date": "2026-02-17",
        "body": "The production server is down.",
        "labels": ["INBOX"],
    }
    path = watcher.create_action_file(item)
    content = path.read_text()
    assert "priority: high" in content


def test_action_file_has_low_priority_for_newsletter(vault, mock_gmail_service):
    """Action file should have priority: low for newsletter senders."""
    from src.watchers.gmail_watcher import GmailWatcher
    watcher = GmailWatcher(vault_path=vault, gmail_service=mock_gmail_service)
    item = {
        "id": "msg_news",
        "from": "newsletter@blog.com",
        "subject": "Weekly Digest",
        "date": "2026-02-17",
        "body": "This week's top stories.",
        "labels": ["INBOX"],
    }
    path = watcher.create_action_file(item)
    content = path.read_text()
    assert "priority: low" in content


def test_action_file_has_high_priority_for_vip_sender(vault, mock_gmail_service):
    """Action file should have priority: high for VIP senders."""
    from src.watchers.gmail_watcher import GmailWatcher
    watcher = GmailWatcher(
        vault_path=vault, gmail_service=mock_gmail_service,
        vip_senders=["ceo@company.com"],
    )
    item = {
        "id": "msg_vip",
        "from": "ceo@company.com",
        "subject": "Quick question",
        "date": "2026-02-17",
        "body": "Can you check something?",
        "labels": ["INBOX"],
    }
    path = watcher.create_action_file(item)
    content = path.read_text()
    assert "priority: high" in content
