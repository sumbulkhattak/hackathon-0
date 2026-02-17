"""Tests for src/briefing.py — Monday Morning CEO Briefing generator."""
import json
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from setup_vault import setup_vault


@pytest.fixture
def vault(tmp_path):
    """Create a fully initialized vault for testing."""
    setup_vault(tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# get_period_stats
# ---------------------------------------------------------------------------


def test_get_period_stats_empty_logs(vault):
    """get_period_stats should return all-zero stats when no log files exist."""
    from src.briefing import get_period_stats

    stats = get_period_stats(vault, period_days=7)
    assert stats["emails_sent"] == 0
    assert stats["plans_created"] == 0
    assert stats["auto_approved"] == 0
    assert stats["manually_approved"] == 0
    assert stats["rejected"] == 0
    assert stats["errors"] == 0
    assert stats["total_actions"] == 0


def test_get_period_stats_counts_actions(vault):
    """get_period_stats should count different action types from log entries."""
    from src.briefing import get_period_stats

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entries = [
        {"timestamp": f"{today}T10:00:00+00:00", "actor": "orchestrator",
         "action": "email_sent", "source": "plan-a.md", "result": "reply_to:x@x.com"},
        {"timestamp": f"{today}T10:01:00+00:00", "actor": "orchestrator",
         "action": "email_sent", "source": "plan-b.md", "result": "reply_to:y@y.com"},
        {"timestamp": f"{today}T10:02:00+00:00", "actor": "orchestrator",
         "action": "plan_created", "source": "email-c.md", "result": "pending_approval:plan-c.md"},
        {"timestamp": f"{today}T10:03:00+00:00", "actor": "orchestrator",
         "action": "auto_approved", "source": "email-d.md", "result": "confidence:0.95"},
        {"timestamp": f"{today}T10:04:00+00:00", "actor": "orchestrator",
         "action": "executed", "source": "plan-e.md", "result": "moved_to_done"},
        {"timestamp": f"{today}T10:05:00+00:00", "actor": "orchestrator",
         "action": "rejection_reviewed", "source": "plan-f.md", "result": "learning_added"},
        {"timestamp": f"{today}T10:06:00+00:00", "actor": "orchestrator",
         "action": "send_failed", "source": "plan-g.md", "result": "error"},
    ]
    log_file = vault / "Logs" / f"{today}.json"
    log_file.write_text(json.dumps(entries, indent=2))

    stats = get_period_stats(vault, period_days=7)
    assert stats["emails_sent"] == 2
    assert stats["plans_created"] == 1
    assert stats["auto_approved"] == 1
    assert stats["manually_approved"] == 1  # "executed" counts as manually approved
    assert stats["rejected"] == 1
    assert stats["errors"] == 1
    assert stats["total_actions"] == 7


def test_get_period_stats_filters_by_period(vault):
    """get_period_stats should only count log entries within the period."""
    from src.briefing import get_period_stats

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    old_date = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%d")

    # Today's log — should be counted
    today_entries = [
        {"timestamp": f"{today}T10:00:00+00:00", "actor": "orchestrator",
         "action": "email_sent", "source": "plan-a.md", "result": "reply_to:x@x.com"},
    ]
    (vault / "Logs" / f"{today}.json").write_text(json.dumps(today_entries, indent=2))

    # Old log — should NOT be counted with period_days=7
    old_entries = [
        {"timestamp": f"{old_date}T10:00:00+00:00", "actor": "orchestrator",
         "action": "email_sent", "source": "plan-old.md", "result": "reply_to:old@old.com"},
        {"timestamp": f"{old_date}T10:01:00+00:00", "actor": "orchestrator",
         "action": "plan_created", "source": "email-old.md", "result": "pending"},
    ]
    (vault / "Logs" / f"{old_date}.json").write_text(json.dumps(old_entries, indent=2))

    stats = get_period_stats(vault, period_days=7)
    assert stats["emails_sent"] == 1
    assert stats["total_actions"] == 1


# ---------------------------------------------------------------------------
# get_completed_items
# ---------------------------------------------------------------------------


def test_get_completed_items_empty(vault):
    """get_completed_items should return empty list when Done/ is empty."""
    from src.briefing import get_completed_items

    items = get_completed_items(vault, period_days=7)
    assert items == []


def test_get_completed_items_returns_recent_files(vault):
    """get_completed_items should return names of recently modified files in Done/."""
    from src.briefing import get_completed_items

    # Create files in Done/ — they are new so they are "recent"
    (vault / "Done" / "plan-invoice-client-a.md").write_text("done A")
    (vault / "Done" / "plan-meeting-response.md").write_text("done B")

    items = get_completed_items(vault, period_days=7)
    assert len(items) == 2
    assert "plan-invoice-client-a.md" in items
    assert "plan-meeting-response.md" in items


def test_get_completed_items_excludes_old_files(vault):
    """get_completed_items should exclude files older than the period."""
    from src.briefing import get_completed_items

    # Create a file and set its mtime to 10 days ago
    old_file = vault / "Done" / "plan-old-task.md"
    old_file.write_text("old done")
    old_mtime = time.time() - (10 * 86400)
    os.utime(str(old_file), (old_mtime, old_mtime))

    # Create a recent file
    (vault / "Done" / "plan-recent-task.md").write_text("recent done")

    items = get_completed_items(vault, period_days=7)
    assert "plan-recent-task.md" in items
    assert "plan-old-task.md" not in items


# ---------------------------------------------------------------------------
# get_bottlenecks
# ---------------------------------------------------------------------------


def test_get_bottlenecks_empty(vault):
    """get_bottlenecks should return empty list when no pending items exist."""
    from src.briefing import get_bottlenecks

    bottlenecks = get_bottlenecks(vault)
    assert bottlenecks == []


def test_get_bottlenecks_finds_old_pending_items(vault):
    """get_bottlenecks should find items in Pending_Approval/ older than 24h."""
    from src.briefing import get_bottlenecks

    old_file = vault / "Pending_Approval" / "plan-complex-request.md"
    old_file.write_text("waiting for approval")
    old_mtime = time.time() - (48 * 3600)  # 48 hours ago
    os.utime(str(old_file), (old_mtime, old_mtime))

    bottlenecks = get_bottlenecks(vault)
    assert len(bottlenecks) == 1
    assert bottlenecks[0]["name"] == "plan-complex-request.md"
    assert bottlenecks[0]["folder"] == "Pending_Approval"
    assert bottlenecks[0]["age_hours"] >= 47  # At least ~48 hours


def test_get_bottlenecks_skips_recent_items(vault):
    """get_bottlenecks should skip items less than 24 hours old."""
    from src.briefing import get_bottlenecks

    # Create a fresh file — should NOT be a bottleneck
    (vault / "Pending_Approval" / "plan-new-request.md").write_text("fresh")

    bottlenecks = get_bottlenecks(vault)
    assert bottlenecks == []


# ---------------------------------------------------------------------------
# generate_briefing
# ---------------------------------------------------------------------------


def test_generate_briefing_returns_markdown(vault):
    """generate_briefing should return a non-empty markdown string."""
    from src.briefing import generate_briefing

    md = generate_briefing(vault)
    assert isinstance(md, str)
    assert len(md) > 0
    assert "# Monday Morning CEO Briefing" in md


def test_generate_briefing_includes_all_sections(vault):
    """generate_briefing should include all required sections."""
    from src.briefing import generate_briefing

    md = generate_briefing(vault)
    assert "## Executive Summary" in md
    assert "## Activity This Period" in md
    assert "## Completed Tasks" in md
    assert "## Bottlenecks" in md
    assert "## Pending Items" in md
    assert "## Proactive Suggestions" in md
    assert "*Generated by Digital FTE" in md


def test_generate_briefing_shows_activity_table(vault):
    """generate_briefing should include an activity table with metric rows."""
    from src.briefing import generate_briefing

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entries = [
        {"timestamp": f"{today}T10:00:00+00:00", "actor": "orchestrator",
         "action": "email_sent", "source": "plan-a.md", "result": "reply_to:x@x.com"},
        {"timestamp": f"{today}T10:01:00+00:00", "actor": "orchestrator",
         "action": "plan_created", "source": "email-b.md", "result": "pending"},
    ]
    (vault / "Logs" / f"{today}.json").write_text(json.dumps(entries, indent=2))

    md = generate_briefing(vault)
    assert "| Metric | Count |" in md
    assert "| Emails processed |" in md
    assert "| Plans created |" in md


# ---------------------------------------------------------------------------
# save_briefing
# ---------------------------------------------------------------------------


def test_save_briefing_creates_file(vault):
    """save_briefing should write the briefing content to a file."""
    from src.briefing import save_briefing

    content = "# Monday Morning CEO Briefing\n\nTest briefing."
    path = save_briefing(vault, content)
    assert path.exists()
    assert path.read_text(encoding="utf-8") == content


def test_save_briefing_uses_date_format(vault):
    """save_briefing should name the file YYYY-MM-DD_Briefing.md."""
    from src.briefing import save_briefing

    content = "# Test Briefing"
    path = save_briefing(vault, content)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    assert path.name == f"{today}_Briefing.md"
    assert path.parent.name == "Briefings"
