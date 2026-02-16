import json
from datetime import datetime, timezone
from pathlib import Path


def test_log_action_creates_daily_log_file(tmp_path):
    """log_action should create a JSON log file named YYYY-MM-DD.json."""
    from src.utils import log_action
    log_action(
        logs_dir=tmp_path,
        actor="gmail_watcher",
        action="email_detected",
        source="msg_123",
        result="action_file_created",
    )
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = tmp_path / f"{today}.json"
    assert log_file.exists()
    entries = json.loads(log_file.read_text())
    assert len(entries) == 1
    assert entries[0]["actor"] == "gmail_watcher"
    assert entries[0]["action"] == "email_detected"


def test_log_action_appends_to_existing(tmp_path):
    """log_action should append to existing daily log, not overwrite."""
    from src.utils import log_action
    log_action(logs_dir=tmp_path, actor="a", action="first", source="s", result="r")
    log_action(logs_dir=tmp_path, actor="b", action="second", source="s", result="r")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entries = json.loads((tmp_path / f"{today}.json").read_text())
    assert len(entries) == 2


def test_slugify():
    """slugify should produce filesystem-safe names."""
    from src.utils import slugify
    assert slugify("Re: Invoice #1234!") == "re-invoice-1234"
    assert slugify("  Hello World  ") == "hello-world"
