"""End-to-end integration test using mocked Gmail service."""
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch


def test_full_email_pipeline(tmp_path):
    from setup_vault import setup_vault
    from src.watchers.gmail_watcher import GmailWatcher
    from src.orchestrator import Orchestrator

    setup_vault(tmp_path)

    service = MagicMock()
    service.users().messages().list.return_value.execute.return_value = {
        "messages": [{"id": "msg_e2e", "threadId": "t1"}]
    }
    service.users().messages().get.return_value.execute.return_value = {
        "id": "msg_e2e",
        "payload": {
            "headers": [
                {"name": "From", "value": "client@example.com"},
                {"name": "Subject", "value": "Project Update"},
                {"name": "Date", "value": "2026-02-16"},
            ],
            "body": {"data": "UHJvamVjdCBpcyBvbiB0cmFjaw=="},
        },
        "labelIds": ["INBOX"],
    }
    service.users().labels().list.return_value.execute.return_value = {
        "labels": [{"id": "L1", "name": "Processed-by-FTE"}]
    }

    # Step 1: Watcher detects email
    watcher = GmailWatcher(vault_path=tmp_path, gmail_service=service)
    count = watcher.run_once()
    assert count == 1
    action_files = list((tmp_path / "Needs_Action").glob("*.md"))
    assert len(action_files) == 1

    # Step 2: Orchestrator processes action
    orch = Orchestrator(vault_path=tmp_path)
    with patch.object(orch, "_invoke_claude") as mock_claude:
        mock_claude.return_value = "## Analysis\nProject status update.\n\n## Recommended Actions\n1. Acknowledge receipt\n\n## Requires Approval\n- [ ] Send reply"
        plan_path = orch.process_action(action_files[0])

    assert plan_path.parent.name == "Pending_Approval"
    assert len(list((tmp_path / "Needs_Action").glob("*.md"))) == 0

    # Step 3: Simulate human approval
    approved_path = tmp_path / "Approved" / plan_path.name
    shutil.move(str(plan_path), str(approved_path))

    # Step 4: Orchestrator executes approved action
    done_path = orch.execute_approved(approved_path)
    assert done_path.parent.name == "Done"
    assert not approved_path.exists()


def test_full_reply_pipeline(tmp_path):
    """End-to-end: email in -> Claude plan with reply -> approve -> send -> done."""
    from setup_vault import setup_vault
    from src.watchers.gmail_watcher import GmailWatcher
    from src.orchestrator import Orchestrator

    setup_vault(tmp_path)

    service = MagicMock()
    service.users().messages().list.return_value.execute.return_value = {
        "messages": [{"id": "msg_reply_e2e", "threadId": "t_reply"}]
    }
    service.users().messages().get.return_value.execute.return_value = {
        "id": "msg_reply_e2e",
        "threadId": "t_reply",
        "payload": {
            "headers": [
                {"name": "From", "value": "client@example.com"},
                {"name": "Subject", "value": "Invoice #99"},
                {"name": "Date", "value": "2026-02-16"},
                {"name": "Message-ID", "value": "<inv99@example.com>"},
            ],
            "body": {"data": "UGxlYXNlIHBheSBpbnZvaWNlICM5OQ=="},
        },
        "labelIds": ["INBOX"],
    }
    service.users().labels().list.return_value.execute.return_value = {
        "labels": [{"id": "L1", "name": "Processed-by-FTE"}]
    }
    service.users().messages().send.return_value.execute.return_value = {
        "id": "sent_reply_1", "threadId": "t_reply",
    }

    # Step 1: Watcher detects email
    watcher = GmailWatcher(vault_path=tmp_path, gmail_service=service)
    count = watcher.run_once()
    assert count == 1
    action_files = list((tmp_path / "Needs_Action").glob("*.md"))
    assert len(action_files) == 1

    # Step 2: Orchestrator processes — Claude returns a reply draft
    orch = Orchestrator(vault_path=tmp_path, gmail_service=service, daily_send_limit=20)
    claude_reply = (
        "## Analysis\nInvoice payment request.\n\n"
        "## Recommended Actions\n1. Acknowledge and confirm payment timeline\n\n"
        "## Requires Approval\n- [ ] Send reply\n\n"
        "## Reply Draft\n"
        "---BEGIN REPLY---\n"
        "Hi,\n\nThank you for Invoice #99. Payment will be processed within 5 business days.\n\n"
        "Best regards\n"
        "---END REPLY---"
    )
    with patch.object(orch, "_invoke_claude") as mock_claude:
        mock_claude.return_value = claude_reply
        plan_path = orch.process_action(action_files[0])

    assert plan_path.parent.name == "Pending_Approval"
    plan_content = plan_path.read_text()
    assert "action: reply" in plan_content
    assert "---BEGIN REPLY---" in plan_content

    # Step 3: Simulate human approval
    approved_path = tmp_path / "Approved" / plan_path.name
    shutil.move(str(plan_path), str(approved_path))

    # Step 4: Orchestrator sends the reply
    done_path = orch.execute_approved(approved_path)
    assert done_path.parent.name == "Done"
    assert not approved_path.exists()
    service.users().messages().send.assert_called_once()


def test_rejection_feedback_loop(tmp_path):
    """End-to-end: email -> plan -> reject -> learning added to Agent Memory."""
    from setup_vault import setup_vault
    from src.watchers.gmail_watcher import GmailWatcher
    from src.orchestrator import Orchestrator

    setup_vault(tmp_path)

    service = MagicMock()
    service.users().messages().list.return_value.execute.return_value = {
        "messages": [{"id": "msg_rej_e2e", "threadId": "t_rej"}]
    }
    service.users().messages().get.return_value.execute.return_value = {
        "id": "msg_rej_e2e",
        "threadId": "t_rej",
        "payload": {
            "headers": [
                {"name": "From", "value": "vip@example.com"},
                {"name": "Subject", "value": "Urgent Request"},
                {"name": "Date", "value": "2026-02-16"},
            ],
            "body": {"data": "SSBuZWVkIHRoaXMgZG9uZSBBU0FQ"},
        },
        "labelIds": ["INBOX"],
    }
    service.users().labels().list.return_value.execute.return_value = {
        "labels": [{"id": "L1", "name": "Processed-by-FTE"}]
    }

    # Step 1: Watcher detects email
    watcher = GmailWatcher(vault_path=tmp_path, gmail_service=service)
    watcher.run_once()
    action_files = list((tmp_path / "Needs_Action").glob("*.md"))
    assert len(action_files) == 1

    # Step 2: Orchestrator creates plan with a reply
    orch = Orchestrator(vault_path=tmp_path, gmail_service=service)
    claude_plan = (
        "## Analysis\nUrgent request from VIP.\n\n"
        "## Recommended Actions\n1. Reply immediately\n\n"
        "## Requires Approval\n- [ ] Send reply\n\n"
        "## Reply Draft\n"
        "---BEGIN REPLY---\n"
        "Dear Sir/Madam,\n\nI have received your request and will process it.\n\n"
        "Yours faithfully\n"
        "---END REPLY---"
    )
    with patch.object(orch, "_invoke_claude") as mock_claude:
        mock_claude.return_value = claude_plan
        plan_path = orch.process_action(action_files[0])

    assert plan_path.parent.name == "Pending_Approval"

    # Step 3: Human rejects the plan (too formal)
    rejected_path = tmp_path / "Rejected" / plan_path.name
    shutil.move(str(plan_path), str(rejected_path))

    # Step 4: Orchestrator reviews rejection and learns
    with patch.object(orch, "_invoke_claude_review") as mock_review:
        mock_review.return_value = "Don't use 'Dear Sir/Madam' or 'Yours faithfully'. Match the sender's informal tone."
        done_path = orch.review_rejected(rejected_path)

    assert done_path.parent.name == "Done"
    assert not rejected_path.exists()

    # Step 5: Verify learning was added to Agent Memory
    memory_content = (tmp_path / "Agent_Memory.md").read_text()
    assert "Don't use 'Dear Sir/Madam'" in memory_content
