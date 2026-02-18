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


def test_process_action_auto_approves_high_confidence(vault):
    """process_action should auto-approve and execute when confidence >= threshold."""
    from src.orchestrator import Orchestrator
    mock_gmail = MagicMock()
    mock_gmail.users().messages().get.return_value.execute.return_value = {
        "id": "msg_auto1", "threadId": "t1",
        "payload": {"headers": [{"name": "Message-ID", "value": "<orig@test.com>"}]},
    }
    mock_gmail.users().messages().send.return_value.execute.return_value = {
        "id": "sent_auto1", "threadId": "t1",
    }
    orch = Orchestrator(
        vault_path=vault, gmail_service=mock_gmail,
        auto_approve_threshold=0.8,
    )
    action_file = vault / "Needs_Action" / "email-auto-test.md"
    action_file.write_text(
        "---\ntype: email\nfrom: bob@test.com\nsubject: Hello\ngmail_id: msg_auto1\n---\n# Test\n\n## Body\nHi there"
    )
    claude_response = (
        "## Analysis\nSimple greeting.\n\n"
        "## Recommended Actions\n1. Reply with acknowledgment\n\n"
        "## Requires Approval\n- [ ] Send reply\n\n"
        "## Reply Draft\n"
        "---BEGIN REPLY---\nHi Bob,\n\nThanks for reaching out!\n\nBest\n---END REPLY---\n\n"
        "## Confidence\n0.92"
    )
    with patch.object(orch, "_invoke_claude") as mock_claude:
        mock_claude.return_value = claude_response
        result_path = orch.process_action(action_file)
    # Should end up in Done/, not Pending_Approval/
    assert result_path.parent.name == "Done"
    assert not action_file.exists()
    assert len(list((vault / "Pending_Approval").glob("*.md"))) == 0
    mock_gmail.users().messages().send.assert_called_once()


def test_process_action_routes_to_pending_below_threshold(vault):
    """process_action should route to Pending_Approval when confidence < threshold."""
    from src.orchestrator import Orchestrator
    orch = Orchestrator(vault_path=vault, auto_approve_threshold=0.9)
    action_file = vault / "Needs_Action" / "email-low-conf.md"
    action_file.write_text(
        "---\ntype: email\nfrom: bob@test.com\nsubject: Hello\n---\n# Test\n\n## Body\nHi"
    )
    claude_response = (
        "## Analysis\nNeeds review.\n\n"
        "## Recommended Actions\n1. Reply\n\n"
        "## Requires Approval\n- [ ] Send reply\n\n"
        "## Confidence\n0.65"
    )
    with patch.object(orch, "_invoke_claude") as mock_claude:
        mock_claude.return_value = claude_response
        result_path = orch.process_action(action_file)
    assert result_path.parent.name == "Pending_Approval"


def test_auto_approve_disabled_by_default(vault):
    """Default threshold 1.0 should never auto-approve (nothing scores > 1.0)."""
    from src.orchestrator import Orchestrator
    orch = Orchestrator(vault_path=vault)
    action_file = vault / "Needs_Action" / "email-default.md"
    action_file.write_text(
        "---\ntype: email\nfrom: bob@test.com\nsubject: Hi\n---\n# Test"
    )
    claude_response = (
        "## Analysis\nSimple.\n\n"
        "## Confidence\n0.99"
    )
    with patch.object(orch, "_invoke_claude") as mock_claude:
        mock_claude.return_value = claude_response
        result_path = orch.process_action(action_file)
    # threshold=1.0, confidence=0.99 → still goes to Pending_Approval
    assert result_path.parent.name == "Pending_Approval"


def test_auto_approve_respects_send_limit(vault):
    """Auto-approve should route to Pending_Approval when daily send limit is hit."""
    from src.orchestrator import Orchestrator
    mock_gmail = MagicMock()
    orch = Orchestrator(
        vault_path=vault, gmail_service=mock_gmail,
        daily_send_limit=0, auto_approve_threshold=0.5,
    )
    action_file = vault / "Needs_Action" / "email-limit.md"
    action_file.write_text(
        "---\ntype: email\nfrom: bob@test.com\nsubject: Hi\ngmail_id: msg1\n---\n# Test"
    )
    claude_response = (
        "## Analysis\nSimple.\n\n"
        "## Reply Draft\n---BEGIN REPLY---\nHi\n---END REPLY---\n\n"
        "## Confidence\n0.95"
    )
    with patch.object(orch, "_invoke_claude") as mock_claude:
        mock_claude.return_value = claude_response
        result_path = orch.process_action(action_file)
    # Send limit hit → falls back to Pending_Approval
    assert result_path.parent.name == "Pending_Approval"
    mock_gmail.users().messages().send.assert_not_called()


def test_auto_approve_logs_action(vault):
    """Auto-approve should log with action 'auto_approved' and include confidence."""
    import json
    from datetime import datetime, timezone
    from src.orchestrator import Orchestrator
    mock_gmail = MagicMock()
    mock_gmail.users().messages().get.return_value.execute.return_value = {
        "id": "msg_log1", "threadId": "t1",
        "payload": {"headers": [{"name": "Message-ID", "value": "<x@test.com>"}]},
    }
    mock_gmail.users().messages().send.return_value.execute.return_value = {
        "id": "sent_log1", "threadId": "t1",
    }
    orch = Orchestrator(
        vault_path=vault, gmail_service=mock_gmail,
        auto_approve_threshold=0.8,
    )
    action_file = vault / "Needs_Action" / "email-log-test.md"
    action_file.write_text(
        "---\ntype: email\nfrom: alice@test.com\nsubject: Test\ngmail_id: msg_log1\n---\n# Test"
    )
    claude_response = (
        "## Analysis\nSimple.\n\n"
        "## Reply Draft\n---BEGIN REPLY---\nHi\n---END REPLY---\n\n"
        "## Confidence\n0.90"
    )
    with patch.object(orch, "_invoke_claude") as mock_claude:
        mock_claude.return_value = claude_response
        orch.process_action(action_file)
    # Check logs for auto_approved entry
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = vault / "Logs" / f"{today}.json"
    assert log_file.exists()
    entries = json.loads(log_file.read_text())
    auto_entries = [e for e in entries if e["action"] == "auto_approved"]
    assert len(auto_entries) >= 1
    assert "confidence:0.9" in auto_entries[0]["result"]


def test_auto_approve_failed_send_falls_back(vault):
    """Auto-approve should move plan to Pending_Approval if send fails."""
    from src.orchestrator import Orchestrator
    mock_gmail = MagicMock()
    mock_gmail.users().messages().get.return_value.execute.return_value = {
        "id": "msg_fail1", "threadId": "t1",
        "payload": {"headers": [{"name": "Message-ID", "value": "<x@test.com>"}]},
    }
    mock_gmail.users().messages().send.return_value.execute.side_effect = Exception("API error")
    orch = Orchestrator(
        vault_path=vault, gmail_service=mock_gmail,
        auto_approve_threshold=0.5,
    )
    action_file = vault / "Needs_Action" / "email-fail-test.md"
    action_file.write_text(
        "---\ntype: email\nfrom: bob@test.com\nsubject: Hi\ngmail_id: msg_fail1\n---\n# Test"
    )
    claude_response = (
        "## Analysis\nSimple.\n\n"
        "## Reply Draft\n---BEGIN REPLY---\nHi\n---END REPLY---\n\n"
        "## Confidence\n0.95"
    )
    with patch.object(orch, "_invoke_claude") as mock_claude:
        mock_claude.return_value = claude_response
        result_path = orch.process_action(action_file)
    # Failed send → plan should be in Pending_Approval for human review
    assert result_path.parent.name == "Pending_Approval"


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


def test_get_pending_actions_sorted_by_priority(tmp_path):
    """get_pending_actions should return high-priority files before normal, then low."""
    from setup_vault import setup_vault
    from src.orchestrator import Orchestrator

    setup_vault(tmp_path)

    # Create action files with different priorities
    (tmp_path / "Needs_Action" / "email-low.md").write_text(
        "---\npriority: low\n---\n# Low priority email", encoding="utf-8"
    )
    (tmp_path / "Needs_Action" / "email-normal.md").write_text(
        "---\npriority: normal\n---\n# Normal priority email", encoding="utf-8"
    )
    (tmp_path / "Needs_Action" / "email-high.md").write_text(
        "---\npriority: high\n---\n# High priority email", encoding="utf-8"
    )

    orch = Orchestrator(vault_path=tmp_path)
    actions = orch.get_pending_actions()

    assert len(actions) == 3
    assert actions[0].name == "email-high.md"
    assert actions[2].name == "email-low.md"


def test_get_pending_actions_handles_missing_priority(tmp_path):
    """Files without priority frontmatter should be treated as normal."""
    from setup_vault import setup_vault
    from src.orchestrator import Orchestrator

    setup_vault(tmp_path)

    (tmp_path / "Needs_Action" / "email-high.md").write_text(
        "---\npriority: high\n---\n# High", encoding="utf-8"
    )
    (tmp_path / "Needs_Action" / "email-nofm.md").write_text(
        "# No frontmatter email", encoding="utf-8"
    )

    orch = Orchestrator(vault_path=tmp_path)
    actions = orch.get_pending_actions()

    assert len(actions) == 2
    assert actions[0].name == "email-high.md"


# --- Work Zone Tests ---

def test_orchestrator_stores_work_zone(vault):
    """Orchestrator should accept and store work_zone parameter."""
    from src.orchestrator import Orchestrator
    orch = Orchestrator(vault_path=vault, work_zone="cloud")
    assert orch.work_zone == "cloud"


def test_orchestrator_work_zone_default_local(vault):
    """Orchestrator should default work_zone to 'local'."""
    from src.orchestrator import Orchestrator
    orch = Orchestrator(vault_path=vault)
    assert orch.work_zone == "local"


def test_cloud_zone_never_auto_approves(vault):
    """Cloud zone should always route to Pending_Approval, even with high confidence."""
    from src.orchestrator import Orchestrator
    orch = Orchestrator(
        vault_path=vault, auto_approve_threshold=0.5, work_zone="cloud"
    )
    action_file = vault / "Needs_Action" / "email-cloud-test.md"
    action_file.write_text(
        "---\ntype: email\nfrom: bob@test.com\nsubject: Hi\ngmail_id: msg1\n---\n# Test"
    )
    claude_response = (
        "## Analysis\nSimple.\n\n"
        "## Reply Draft\n---BEGIN REPLY---\nHi\n---END REPLY---\n\n"
        "## Confidence\n0.99"
    )
    with patch.object(orch, "_invoke_claude") as mock_claude:
        mock_claude.return_value = claude_response
        result_path = orch.process_action(action_file)
    # Cloud zone → always Pending_Approval, never auto-approved
    assert result_path.parent.name == "Pending_Approval"


def test_cloud_zone_blocks_execution(vault):
    """Cloud zone should block execute_approved and return the file as-is."""
    from src.orchestrator import Orchestrator
    orch = Orchestrator(vault_path=vault, work_zone="cloud")
    approved_file = vault / "Approved" / "plan-cloud-block.md"
    approved_file.write_text("---\nstatus: approved\n---\n# Plan\nDo something.")
    result = orch.execute_approved(approved_file)
    # File should stay in Approved, not moved to Done
    assert result == approved_file
    assert approved_file.exists()
    assert not (vault / "Done" / "plan-cloud-block.md").exists()


def test_local_zone_allows_execution(vault):
    """Local zone should execute approved actions normally."""
    from src.orchestrator import Orchestrator
    orch = Orchestrator(vault_path=vault, work_zone="local")
    approved_file = vault / "Approved" / "plan-local-exec.md"
    approved_file.write_text("---\nstatus: approved\n---\n# Plan\nDo something.")
    result = orch.execute_approved(approved_file)
    assert result.parent.name == "Done"
    assert not approved_file.exists()
