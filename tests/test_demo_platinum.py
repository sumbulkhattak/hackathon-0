"""Tests for the Platinum demo gate flow."""
import json
from pathlib import Path

import pytest

from setup_vault import setup_vault


@pytest.fixture
def vault(tmp_path):
    """Create a full vault for demo testing."""
    setup_vault(tmp_path)
    return tmp_path


def test_domain_subdirs_created(vault):
    """setup_vault should create domain-specific subdirectories."""
    for domain in ["email", "file", "social"]:
        assert (vault / "Needs_Action" / domain).is_dir()
        assert (vault / "Plans" / domain).is_dir()
        assert (vault / "Pending_Approval" / domain).is_dir()


def test_platinum_demo_flow(vault):
    """Simulate the full Platinum demo gate: email -> cloud draft -> approve -> execute -> done."""
    import shutil
    from datetime import datetime, timezone
    from src.utils import log_action
    from src.vault_sync import write_update, merge_updates
    from src.dashboard import update_dashboard

    # Step 1: Email arrives in Needs_Action/email/
    email_file = vault / "Needs_Action" / "email" / "email-demo-test.md"
    email_file.write_text("---\ntype: email\nfrom: test@example.com\nsubject: Test\npriority: high\ngmail_id: demo123\n---\n# Test email\n")
    assert email_file.exists()

    # Step 2: Cloud drafts plan to Pending_Approval/email/
    plan_file = vault / "Pending_Approval" / "email" / "plan-demo-test.md"
    plan_file.write_text("---\nsource: email-demo-test.md\nconfidence: 0.92\naction: reply\n---\n# Plan\nReply to test\n")
    email_file.unlink()
    assert plan_file.exists()
    assert not email_file.exists()

    # Step 3: Cloud writes update signal
    write_update(vault, "cloud-test-update.md", "Cloud drafted reply")
    assert (vault / "Updates" / "cloud-test-update.md").exists()

    # Step 4: Local merges updates
    merged = merge_updates(vault)
    assert merged == 1
    assert not (vault / "Updates" / "cloud-test-update.md").exists()
    dashboard_content = (vault / "Dashboard.md").read_text(encoding="utf-8")
    assert "Cloud drafted reply" in dashboard_content

    # Step 5: User approves (move to Approved/email/)
    approved_file = vault / "Approved" / "email" / "plan-demo-test.md"
    approved_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(plan_file), str(approved_file))
    assert approved_file.exists()
    assert not plan_file.exists()

    # Step 6: Local executes (simulated) and moves to Done
    log_action(
        logs_dir=vault / "Logs",
        actor="orchestrator",
        action="email_sent",
        source="plan-demo-test.md",
        result="reply_to:test@example.com",
    )
    done_file = vault / "Done" / "plan-demo-test.md"
    shutil.move(str(approved_file), str(done_file))
    assert done_file.exists()
    assert not approved_file.exists()

    # Verify log entry
    log_files = list((vault / "Logs").glob("*.json"))
    assert len(log_files) >= 1
    entries = json.loads(log_files[0].read_text(encoding="utf-8"))
    assert any(e["action"] == "email_sent" for e in entries)

    # Verify final vault state
    assert len(list((vault / "Needs_Action").rglob("*.md"))) == 0
    assert len(list((vault / "Pending_Approval").rglob("*.md"))) == 0
    assert len(list((vault / "Approved").rglob("*.md"))) == 0
    assert len(list((vault / "Done").glob("*.md"))) == 1
