import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


@pytest.fixture
def vault(tmp_path):
    for folder in ["Needs_Action", "Plans", "Pending_Approval", "Approved", "Done", "Logs", "Rejected"]:
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


def test_orchestrator_detects_rejected_files(vault):
    """get_rejected_actions should find files in Rejected/ folder."""
    from src.orchestrator import Orchestrator
    orch = Orchestrator(vault_path=vault)
    rejected_file = vault / "Rejected" / "plan-bad.md"
    rejected_file.write_text("---\nstatus: pending_approval\n---\n\n# Plan\nBad plan.")
    rejected = orch.get_rejected_actions()
    assert len(rejected) == 1
    assert rejected[0].name == "plan-bad.md"


def make_rejected_plan(vault, name="plan-rejected-test.md"):
    """Helper: create a rejected plan file."""
    content = """---
source: email-test.md
created: 2026-02-16T10:00:00Z
status: pending_approval
action: reply
gmail_id: msg_rej1
to: bob@test.com
subject: "Re: Hello"
---

# Plan: email-test

## Analysis
General greeting.

## Reply Draft
---BEGIN REPLY---
Dear Sir/Madam,

I hereby acknowledge your correspondence.

Yours faithfully
---END REPLY---
"""
    path = vault / "Rejected" / name
    path.write_text(content)
    return path


def test_review_rejected_moves_to_done(vault):
    """review_rejected should move the file to Done/ after review."""
    from src.orchestrator import Orchestrator
    orch = Orchestrator(vault_path=vault)
    rejected = make_rejected_plan(vault)
    with patch.object(orch, "_invoke_claude_review") as mock_review:
        mock_review.return_value = "Don't use overly formal language. Match the sender's casual tone."
        orch.review_rejected(rejected)
    assert not rejected.exists()
    assert (vault / "Done" / "plan-rejected-test.md").exists()


def test_review_rejected_appends_learning_to_memory(vault):
    """review_rejected should append the learning to Agent_Memory.md."""
    from src.orchestrator import Orchestrator
    memory_path = vault / "Agent_Memory.md"
    memory_path.write_text("# Agent Memory\n\n## Patterns\n")
    orch = Orchestrator(vault_path=vault)
    rejected = make_rejected_plan(vault)
    with patch.object(orch, "_invoke_claude_review") as mock_review:
        mock_review.return_value = "Don't use overly formal language."
        orch.review_rejected(rejected)
    content = memory_path.read_text()
    assert "Don't use overly formal language." in content


def test_review_rejected_handles_claude_failure(vault):
    """review_rejected should still move to Done if Claude fails."""
    from src.orchestrator import Orchestrator
    orch = Orchestrator(vault_path=vault)
    rejected = make_rejected_plan(vault)
    with patch.object(orch, "_invoke_claude_review") as mock_review:
        mock_review.return_value = ""
        orch.review_rejected(rejected)
    assert not rejected.exists()
    assert (vault / "Done" / "plan-rejected-test.md").exists()


def test_review_rejected_creates_memory_if_missing(vault):
    """review_rejected should create Agent_Memory.md if it doesn't exist."""
    from src.orchestrator import Orchestrator
    orch = Orchestrator(vault_path=vault)
    rejected = make_rejected_plan(vault)
    memory_path = vault / "Agent_Memory.md"
    assert not memory_path.exists()
    with patch.object(orch, "_invoke_claude_review") as mock_review:
        mock_review.return_value = "A useful learning."
        orch.review_rejected(rejected)
    assert memory_path.exists()
    content = memory_path.read_text()
    assert "A useful learning." in content


def test_orchestrator_stores_auto_approve_threshold(vault):
    """Orchestrator should accept and store auto_approve_threshold."""
    from src.orchestrator import Orchestrator
    orch = Orchestrator(vault_path=vault, auto_approve_threshold=0.85)
    assert orch.auto_approve_threshold == 0.85


def test_orchestrator_auto_approve_threshold_default(vault):
    """Orchestrator should default auto_approve_threshold to 1.0."""
    from src.orchestrator import Orchestrator
    orch = Orchestrator(vault_path=vault)
    assert orch.auto_approve_threshold == 1.0


def test_invoke_claude_prompt_requests_confidence(vault):
    """_invoke_claude prompt should ask Claude for a ## Confidence section."""
    from src.orchestrator import Orchestrator
    orch = Orchestrator(vault_path=vault)
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="## Analysis\nTest.")
        orch._invoke_claude("Test action", "Test handbook")
        call_args = mock_run.call_args[0][0]
        prompt = call_args[-1]
        assert "## Confidence" in prompt
        assert "0.0 to 1.0" in prompt


def test_invoke_claude_includes_agent_memory(vault):
    """_invoke_claude should include Agent_Memory.md content in the prompt."""
    from src.orchestrator import Orchestrator
    memory_path = vault / "Agent_Memory.md"
    memory_path.write_text("# Agent Memory\n\n## Patterns\n- Don't be overly formal.\n")
    orch = Orchestrator(vault_path=vault)
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="## Analysis\nTest response.")
        orch._invoke_claude("Test action content", "Test handbook")
        call_args = mock_run.call_args[0][0]
        prompt = call_args[-1]  # Last arg is the prompt string
        assert "Agent Memory" in prompt
        assert "Don't be overly formal." in prompt
