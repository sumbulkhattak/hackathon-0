"""Tests for the Ralph Wiggum autonomous loop."""
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture
def vault(tmp_path):
    """Create a minimal vault structure for testing."""
    for folder in ["Inbox", "Needs_Action", "Plans", "Pending_Approval",
                    "Approved", "Done", "Logs", "Incoming_Files", "Rejected",
                    "Briefings"]:
        (tmp_path / folder).mkdir()
    return tmp_path


# ── check_promise_completion ───────────────────────────────────────────


def test_check_promise_completion_found():
    """Return True when output contains <promise>TASK_COMPLETE</promise>."""
    from src.ralph_wiggum import check_promise_completion
    output = "I've finished everything.\n<promise>TASK_COMPLETE</promise>\nDone."
    assert check_promise_completion(output) is True


def test_check_promise_completion_not_found():
    """Return False when output does not contain the promise tag."""
    from src.ralph_wiggum import check_promise_completion
    output = "Still working on the task, need more iterations."
    assert check_promise_completion(output) is False


def test_check_promise_completion_partial_tag():
    """Return False for incomplete/partial promise tags."""
    from src.ralph_wiggum import check_promise_completion
    assert check_promise_completion("<promise>TASK_COMPLETE") is False
    assert check_promise_completion("TASK_COMPLETE</promise>") is False
    assert check_promise_completion("<promise>PARTIAL</promise>") is False


# ── check_file_completion ──────────────────────────────────────────────


def test_check_file_completion_file_in_done(vault):
    """Return True when the task file exists in Done/ directory."""
    from src.ralph_wiggum import check_file_completion
    task_file = vault / "Needs_Action" / "task-123.md"
    done_dir = vault / "Done"
    # Simulate file moved to Done
    (done_dir / "task-123.md").write_text("# Task done")
    assert check_file_completion(task_file, done_dir) is True


def test_check_file_completion_file_not_in_done(vault):
    """Return False when the task file is not in Done/ directory."""
    from src.ralph_wiggum import check_file_completion
    task_file = vault / "Needs_Action" / "task-123.md"
    task_file.write_text("# Task pending")
    done_dir = vault / "Done"
    assert check_file_completion(task_file, done_dir) is False


# ── create_task_state ──────────────────────────────────────────────────


def test_create_task_state_creates_file(vault):
    """create_task_state should create a state file in the vault."""
    from src.ralph_wiggum import create_task_state
    state_path = create_task_state(vault, "Summarize all emails", iteration=0)
    assert state_path.exists()
    content = state_path.read_text()
    assert "Summarize all emails" in content


def test_create_task_state_includes_iteration(vault):
    """State file should record the current iteration number."""
    from src.ralph_wiggum import create_task_state
    state_path = create_task_state(
        vault, "Summarize all emails", iteration=3, previous_output="partial result"
    )
    content = state_path.read_text()
    assert "3" in content
    assert "partial result" in content


# ── run_ralph_loop ─────────────────────────────────────────────────────


def test_run_ralph_loop_completes_on_promise(vault):
    """Loop should complete when Claude returns TASK_COMPLETE promise."""
    from src.ralph_wiggum import run_ralph_loop
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "All done!\n<promise>TASK_COMPLETE</promise>"
    with patch("subprocess.run", return_value=mock_result):
        result = run_ralph_loop(
            vault_path=vault,
            task_prompt="Summarize emails",
            max_iterations=5,
            completion_strategy="promise",
        )
    assert result["completed"] is True
    assert result["iterations"] == 1
    assert result["strategy"] == "promise"
    assert "<promise>TASK_COMPLETE</promise>" in result["output"]


def test_run_ralph_loop_stops_at_max_iterations(vault):
    """Loop should stop after max_iterations and report incomplete."""
    from src.ralph_wiggum import run_ralph_loop
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Still working on it..."
    with patch("subprocess.run", return_value=mock_result):
        result = run_ralph_loop(
            vault_path=vault,
            task_prompt="Hard task",
            max_iterations=3,
            completion_strategy="promise",
        )
    assert result["completed"] is False
    assert result["iterations"] == 3


def test_run_ralph_loop_file_movement_strategy(vault):
    """Loop should complete when task file moves to Done/ directory."""
    from src.ralph_wiggum import run_ralph_loop
    task_file = vault / "Needs_Action" / "task-move.md"
    task_file.write_text("# Task to move")

    call_count = 0

    def fake_subprocess_run(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        # On second call, simulate the file being moved to Done
        if call_count >= 2:
            (vault / "Done" / "task-move.md").write_text("# Task completed")
            if task_file.exists():
                task_file.unlink()
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = f"Iteration {call_count} output"
        return mock

    with patch("subprocess.run", side_effect=fake_subprocess_run):
        result = run_ralph_loop(
            vault_path=vault,
            task_prompt="Move task file",
            max_iterations=5,
            completion_strategy="file_movement",
            task_file=task_file,
        )
    assert result["completed"] is True
    assert result["iterations"] == 2
    assert result["strategy"] == "file_movement"


def test_run_ralph_loop_returns_result_dict(vault):
    """Result dict must contain completed, iterations, strategy, output keys."""
    from src.ralph_wiggum import run_ralph_loop
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Done\n<promise>TASK_COMPLETE</promise>"
    with patch("subprocess.run", return_value=mock_result):
        result = run_ralph_loop(
            vault_path=vault,
            task_prompt="Quick task",
            max_iterations=1,
            completion_strategy="promise",
        )
    assert "completed" in result
    assert "iterations" in result
    assert "strategy" in result
    assert "output" in result


def test_run_ralph_loop_logs_iterations(vault):
    """Each iteration should be logged to vault/Logs/."""
    from src.ralph_wiggum import run_ralph_loop
    call_count = 0

    def fake_run(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        mock = MagicMock()
        mock.returncode = 0
        if call_count >= 2:
            mock.stdout = "Finished!\n<promise>TASK_COMPLETE</promise>"
        else:
            mock.stdout = "Working..."
        return mock

    with patch("subprocess.run", side_effect=fake_run):
        run_ralph_loop(
            vault_path=vault,
            task_prompt="Log test",
            max_iterations=5,
            completion_strategy="promise",
        )
    # Check that a ralph-wiggum log file was created
    log_files = list((vault / "Logs").glob("ralph-wiggum-*.json"))
    assert len(log_files) >= 1
    log_data = json.loads(log_files[0].read_text())
    assert isinstance(log_data, list)
    assert len(log_data) == 2  # two iterations
    assert log_data[0]["iteration"] == 1
    assert log_data[1]["iteration"] == 2
