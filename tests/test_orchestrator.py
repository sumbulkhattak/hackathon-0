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
