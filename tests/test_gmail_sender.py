"""Tests for Gmail reply sending."""
import base64
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.gmail_sender import send_reply, check_send_limit, increment_send_count


@pytest.fixture
def gmail_service():
    service = MagicMock()
    # Mock fetching original message for threadId and Message-ID
    service.users().messages().get.return_value.execute.return_value = {
        "id": "orig_msg_id",
        "threadId": "thread_123",
        "payload": {
            "headers": [
                {"name": "Message-ID", "value": "<original@example.com>"},
            ],
        },
    }
    # Mock sending
    service.users().messages().send.return_value.execute.return_value = {
        "id": "sent_msg_id",
        "threadId": "thread_123",
    }
    return service


def test_send_reply_calls_gmail_send(gmail_service):
    """send_reply should call Gmail API to send the message."""
    result = send_reply(
        gmail_service=gmail_service,
        gmail_id="orig_msg_id",
        to="bob@test.com",
        subject="Re: Hello",
        body="Thanks for your email.",
    )
    gmail_service.users().messages().send.assert_called_once()
    assert result["id"] == "sent_msg_id"
    assert result["threadId"] == "thread_123"


def test_send_reply_includes_thread_id(gmail_service):
    """send_reply should include threadId for proper Gmail threading."""
    send_reply(
        gmail_service=gmail_service,
        gmail_id="orig_msg_id",
        to="bob@test.com",
        subject="Re: Hello",
        body="Thanks.",
    )
    call_args = gmail_service.users().messages().send.call_args
    send_body = call_args[1]["body"] if "body" in call_args[1] else call_args[0][0]
    assert send_body["threadId"] == "thread_123"


def test_send_reply_builds_valid_mime(gmail_service):
    """send_reply should build a base64-encoded MIME message."""
    send_reply(
        gmail_service=gmail_service,
        gmail_id="orig_msg_id",
        to="bob@test.com",
        subject="Re: Hello",
        body="Thanks.",
    )
    call_args = gmail_service.users().messages().send.call_args
    send_body = call_args[1]["body"] if "body" in call_args[1] else call_args[0][0]
    # raw should be a base64url-encoded string
    raw = send_body["raw"]
    decoded = base64.urlsafe_b64decode(raw).decode("utf-8")
    assert "To: bob@test.com" in decoded
    assert "Subject: Re: Hello" in decoded
    assert "Thanks." in decoded
    assert "In-Reply-To: <original@example.com>" in decoded


def test_check_send_limit_under_limit(tmp_path):
    """check_send_limit should return True when under the daily limit."""
    assert check_send_limit(logs_dir=tmp_path, limit=20) is True


def test_check_send_limit_at_limit(tmp_path):
    """check_send_limit should return False when at the daily limit."""
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    count_file = tmp_path / f".send_count_{today}.json"
    count_file.write_text(json.dumps({"count": 20}))
    assert check_send_limit(logs_dir=tmp_path, limit=20) is False


def test_increment_send_count(tmp_path):
    """increment_send_count should increase the daily counter."""
    increment_send_count(logs_dir=tmp_path)
    increment_send_count(logs_dir=tmp_path)

    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    count_file = tmp_path / f".send_count_{today}.json"
    data = json.loads(count_file.read_text())
    assert data["count"] == 2
