import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


@pytest.fixture
def vault(tmp_path):
    for folder in ["Needs_Action", "Plans", "Pending_Approval", "Approved", "Done", "Logs"]:
        (tmp_path / folder).mkdir()
    (tmp_path / "Company_Handbook.md").write_text("# Handbook\nApprove all emails.")
    return tmp_path


def test_orchestrator_detects_new_action_file(vault):
    from src.orchestrator import Orchestrator
    orch = Orchestrator(vault_path=vault)
    action_file = vault / "Needs_Action" / "email-test-abc123.md"
    action_file.write_text("---\ntype: email\n---\n# Test Email")
    pending = orch.get_pending_actions()
    assert len(pending) == 1
    assert pending[0].name == "email-test-abc123.md"


def test_orchestrator_generates_plan(vault):
    from src.orchestrator import Orchestrator
    orch = Orchestrator(vault_path=vault)
    action_file = vault / "Needs_Action" / "email-test-abc123.md"
    action_file.write_text("---\ntype: email\nfrom: bob@test.com\nsubject: Hello\n---\n# Test\n\n## Body\nHi there")
    with patch.object(orch, "_invoke_claude") as mock_claude:
        mock_claude.return_value = "## Analysis\nGeneral greeting.\n\n## Recommended Actions\n1. Reply with acknowledgment\n\n## Requires Approval\n- [ ] Send reply email"
        plan_path = orch.process_action(action_file)
    assert plan_path.exists()
    assert plan_path.parent.name == "Pending_Approval"
    content = plan_path.read_text()
    assert "Analysis" in content
    assert not action_file.exists()


def test_orchestrator_moves_approved_to_done(vault):
    from src.orchestrator import Orchestrator
    orch = Orchestrator(vault_path=vault)
    approved_file = vault / "Approved" / "plan-test.md"
    approved_file.write_text("# Plan\nSend reply.")
    orch.execute_approved(approved_file)
    assert not approved_file.exists()
    assert (vault / "Done" / "plan-test.md").exists()


def make_reply_plan(vault, gmail_id="msg_abc123", to="bob@test.com", subject="Re: Hello"):
    """Helper: create an approved plan file with a reply block."""
    content = f"""---
source: email-test.md
created: 2026-02-16T10:00:00Z
status: pending_approval
action: reply
gmail_id: {gmail_id}
to: {to}
subject: "{subject}"
---

# Plan: email-test

## Analysis
General greeting.

## Reply Draft
---BEGIN REPLY---
Hi Bob,

Thanks for reaching out.

Best regards
---END REPLY---
"""
    path = vault / "Approved" / "plan-test-reply.md"
    path.write_text(content)
    return path


def test_orchestrator_sends_reply_on_approved(vault):
    """execute_approved should call send_reply when action is reply."""
    from src.orchestrator import Orchestrator
    mock_gmail = MagicMock()
    mock_gmail.users().messages().get.return_value.execute.return_value = {
        "id": "msg_abc123",
        "threadId": "t1",
        "payload": {"headers": [{"name": "Message-ID", "value": "<orig@test.com>"}]},
    }
    mock_gmail.users().messages().send.return_value.execute.return_value = {
        "id": "sent_1", "threadId": "t1",
    }
    orch = Orchestrator(vault_path=vault, gmail_service=mock_gmail)
    plan = make_reply_plan(vault)
    orch.execute_approved(plan)
    mock_gmail.users().messages().send.assert_called_once()
    assert not plan.exists()
    assert (vault / "Done" / "plan-test-reply.md").exists()


def test_orchestrator_skips_send_when_no_action(vault):
    """execute_approved should just move to Done when no action field."""
    from src.orchestrator import Orchestrator
    mock_gmail = MagicMock()
    orch = Orchestrator(vault_path=vault, gmail_service=mock_gmail)
    approved_file = vault / "Approved" / "plan-no-action.md"
    approved_file.write_text("---\nsource: email-test.md\nstatus: pending_approval\n---\n\n# Plan\nJust analysis.")
    orch.execute_approved(approved_file)
    mock_gmail.users().messages().send.assert_not_called()
    assert (vault / "Done" / "plan-no-action.md").exists()


def test_orchestrator_respects_daily_send_limit(vault):
    """execute_approved should skip sending when daily limit is reached."""
    from src.orchestrator import Orchestrator
    mock_gmail = MagicMock()
    orch = Orchestrator(vault_path=vault, gmail_service=mock_gmail, daily_send_limit=0)
    plan = make_reply_plan(vault)
    orch.execute_approved(plan)
    mock_gmail.users().messages().send.assert_not_called()
    # File should remain in Approved (not moved to Done)
    assert plan.exists()


def test_orchestrator_handles_missing_reply_block(vault):
    """execute_approved should move to Done with failure when reply block is missing."""
    from src.orchestrator import Orchestrator
    mock_gmail = MagicMock()
    orch = Orchestrator(vault_path=vault, gmail_service=mock_gmail)
    approved_file = vault / "Approved" / "plan-bad-reply.md"
    approved_file.write_text("---\naction: reply\ngmail_id: msg1\nto: a@b.com\nsubject: \"Re: X\"\n---\n\n# Plan\nNo reply block!")
    orch.execute_approved(approved_file)
    mock_gmail.users().messages().send.assert_not_called()
    assert (vault / "Done" / "plan-bad-reply.md").exists()
