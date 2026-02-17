"""Tests for the scheduler module."""
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.scheduler import run_once, generate_cron_entry, generate_task_scheduler_xml


@pytest.fixture()
def vault(tmp_path):
    """Create a minimal vault structure."""
    for folder in [
        "Inbox", "Needs_Action", "Plans", "Pending_Approval",
        "Approved", "Done", "Logs", "Incoming_Files", "Rejected",
    ]:
        (tmp_path / folder).mkdir()
    return tmp_path


def test_run_once_returns_results_dict(vault):
    """run_once should return a dict with expected keys."""
    results = run_once(vault_path=vault)
    assert isinstance(results, dict)
    assert "emails_detected" in results
    assert "files_detected" in results
    assert "actions_processed" in results
    assert "approved_executed" in results
    assert "rejections_reviewed" in results


def test_run_once_no_gmail_service(vault):
    """run_once without gmail_service should skip email detection."""
    results = run_once(vault_path=vault, gmail_service=None)
    assert results["emails_detected"] == 0


def test_run_once_processes_actions(vault):
    """run_once should process action files in Needs_Action/."""
    action = vault / "Needs_Action" / "email-test.md"
    action.write_text("---\ntype: email\npriority: normal\n---\nTest email")

    with patch("src.orchestrator.Orchestrator.process_action") as mock_process:
        mock_process.return_value = vault / "Pending_Approval" / "plan-test.md"
        results = run_once(vault_path=vault)
        assert results["actions_processed"] == 1
        mock_process.assert_called_once()


def test_run_once_executes_approved(vault):
    """run_once should execute approved actions."""
    approved = vault / "Approved" / "plan-approved.md"
    approved.write_text("---\nstatus: approved\n---\nApproved plan")

    with patch("src.orchestrator.Orchestrator.execute_approved") as mock_exec:
        mock_exec.return_value = vault / "Done" / "plan-approved.md"
        results = run_once(vault_path=vault)
        assert results["approved_executed"] == 1


def test_run_once_reviews_rejected(vault):
    """run_once should review rejected plans."""
    rejected = vault / "Rejected" / "plan-bad.md"
    rejected.write_text("---\nstatus: rejected\n---\nBad plan")

    with patch("src.orchestrator.Orchestrator.review_rejected") as mock_review:
        mock_review.return_value = vault / "Done" / "plan-bad.md"
        results = run_once(vault_path=vault)
        assert results["rejections_reviewed"] == 1


def test_run_once_updates_dashboard(vault):
    """run_once should update Dashboard.md."""
    run_once(vault_path=vault)
    dashboard = vault / "Dashboard.md"
    assert dashboard.exists()
    content = dashboard.read_text()
    assert "Digital FTE Dashboard" in content


def test_generate_cron_entry():
    """generate_cron_entry should return a valid crontab line."""
    entry = generate_cron_entry(python_path="python3", project_dir="/home/user/hackathon-0")
    assert "*/5 * * * *" in entry
    assert "python3" in entry
    assert "--once" in entry
    assert "/home/user/hackathon-0" in entry


def test_generate_task_scheduler_xml():
    """generate_task_scheduler_xml should return valid XML."""
    xml = generate_task_scheduler_xml(python_path="python", project_dir="C:\\hackathon-0")
    assert "PT5M" in xml
    assert "python" in xml
    assert "--once" in xml
    assert "C:\\hackathon-0" in xml
