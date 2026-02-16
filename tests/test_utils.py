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


def test_parse_frontmatter_extracts_yaml(tmp_path):
    """parse_frontmatter should extract YAML between --- delimiters."""
    from src.utils import parse_frontmatter
    f = tmp_path / "test.md"
    f.write_text("---\naction: reply\nto: bob@test.com\nsubject: \"Re: Hello\"\n---\n\n# Plan\nSome content.")
    result = parse_frontmatter(f)
    assert result["action"] == "reply"
    assert result["to"] == "bob@test.com"
    assert result["subject"] == "Re: Hello"


def test_parse_frontmatter_returns_empty_on_no_frontmatter(tmp_path):
    """parse_frontmatter should return empty dict when no YAML block exists."""
    from src.utils import parse_frontmatter
    f = tmp_path / "test.md"
    f.write_text("# Just a heading\nNo frontmatter here.")
    result = parse_frontmatter(f)
    assert result == {}


def test_extract_reply_block(tmp_path):
    """extract_reply_block should return text between BEGIN/END REPLY markers."""
    from src.utils import extract_reply_block
    f = tmp_path / "plan.md"
    f.write_text(
        "---\naction: reply\n---\n\n# Plan\n\n## Reply Draft\n"
        "---BEGIN REPLY---\nHi Bob,\n\nThanks for your email.\n\nBest regards\n---END REPLY---\n"
    )
    result = extract_reply_block(f)
    assert result == "Hi Bob,\n\nThanks for your email.\n\nBest regards"


def test_extract_reply_block_returns_none_when_missing(tmp_path):
    """extract_reply_block should return None when no reply block exists."""
    from src.utils import extract_reply_block
    f = tmp_path / "plan.md"
    f.write_text("---\naction: reply\n---\n\n# Plan\nNo reply block here.")
    result = extract_reply_block(f)
    assert result is None
