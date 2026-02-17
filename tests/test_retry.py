"""TDD tests for retry logic with exponential backoff and graceful degradation."""
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, call

import pytest

from src.retry import (
    TransientError,
    PermanentError,
    with_retry,
    queue_failed_action,
    process_quarantine,
)


# ---------------------------------------------------------------------------
# with_retry decorator tests
# ---------------------------------------------------------------------------

def test_with_retry_succeeds_first_try():
    """Decorated function that succeeds immediately should return normally."""
    call_count = 0

    @with_retry(max_attempts=3, base_delay=1)
    def succeed():
        nonlocal call_count
        call_count += 1
        return "ok"

    result = succeed()
    assert result == "ok"
    assert call_count == 1


def test_with_retry_succeeds_after_transient_error():
    """Decorated function should retry and eventually succeed on TransientError."""
    attempts = []

    @with_retry(max_attempts=3, base_delay=0.01)
    def flaky():
        attempts.append(1)
        if len(attempts) < 3:
            raise TransientError("temporary")
        return "recovered"

    with patch("src.retry.time.sleep"):
        result = flaky()
    assert result == "recovered"
    assert len(attempts) == 3


def test_with_retry_gives_up_after_max_attempts():
    """Should raise TransientError after exhausting max_attempts."""
    call_count = 0

    @with_retry(max_attempts=3, base_delay=0.01)
    def always_fail():
        nonlocal call_count
        call_count += 1
        raise TransientError("still broken")

    with patch("src.retry.time.sleep"):
        with pytest.raises(TransientError, match="still broken"):
            always_fail()
    assert call_count == 3


def test_with_retry_does_not_retry_permanent_error():
    """PermanentError should propagate immediately without retry."""
    call_count = 0

    @with_retry(max_attempts=5, base_delay=0.01)
    def permanent_fail():
        nonlocal call_count
        call_count += 1
        raise PermanentError("auth revoked")

    with pytest.raises(PermanentError, match="auth revoked"):
        permanent_fail()
    assert call_count == 1


def test_with_retry_exponential_backoff_delays():
    """Sleep delays should follow exponential backoff: base * 2^attempt."""
    @with_retry(max_attempts=4, base_delay=1, max_delay=60)
    def always_fail():
        raise TransientError("fail")

    with patch("src.retry.time.sleep") as mock_sleep:
        with pytest.raises(TransientError):
            always_fail()
        # Attempts: 1 (fail, sleep 1), 2 (fail, sleep 2), 3 (fail, sleep 4), 4th fail -> raise
        # After attempt 1: delay = 1 * 2^0 = 1
        # After attempt 2: delay = 1 * 2^1 = 2
        # After attempt 3: delay = 1 * 2^2 = 4
        assert mock_sleep.call_count == 3
        assert mock_sleep.call_args_list[0] == call(1)
        assert mock_sleep.call_args_list[1] == call(2)
        assert mock_sleep.call_args_list[2] == call(4)


def test_with_retry_caps_delay_at_max():
    """Sleep delay should be capped at max_delay."""
    @with_retry(max_attempts=6, base_delay=10, max_delay=30)
    def always_fail():
        raise TransientError("fail")

    with patch("src.retry.time.sleep") as mock_sleep:
        with pytest.raises(TransientError):
            always_fail()
        # After attempt 1: min(10*2^0, 30) = 10
        # After attempt 2: min(10*2^1, 30) = 20
        # After attempt 3: min(10*2^2, 30) = 30 (capped)
        # After attempt 4: min(10*2^3, 30) = 30 (capped)
        # After attempt 5: min(10*2^4, 30) = 30 (capped)
        assert mock_sleep.call_count == 5
        assert mock_sleep.call_args_list[2] == call(30)
        assert mock_sleep.call_args_list[3] == call(30)
        assert mock_sleep.call_args_list[4] == call(30)


def test_with_retry_calls_on_failure_callback():
    """on_failure callback should be called with func_name, error, attempt on each failure."""
    callback = MagicMock()

    @with_retry(max_attempts=3, base_delay=0.01, on_failure=callback)
    def flaky_func():
        raise TransientError("oops")

    with patch("src.retry.time.sleep"):
        with pytest.raises(TransientError):
            flaky_func()

    assert callback.call_count == 3
    # Check first call: func_name, error, attempt
    first_call = callback.call_args_list[0]
    assert first_call[0][0] == "flaky_func"  # func_name
    assert isinstance(first_call[0][1], TransientError)  # error
    assert first_call[0][2] == 1  # attempt


# ---------------------------------------------------------------------------
# queue_failed_action tests
# ---------------------------------------------------------------------------

def test_queue_failed_action_creates_quarantine_dir(tmp_path):
    """queue_failed_action should create vault/Quarantine/ if it doesn't exist."""
    vault = tmp_path
    (vault / "Needs_Action").mkdir()
    action = vault / "Needs_Action" / "email-test.md"
    action.write_text("---\ntype: email\n---\n# Test", encoding="utf-8")

    queue_failed_action(vault, action, "API timeout")

    assert (vault / "Quarantine").is_dir()


def test_queue_failed_action_moves_file(tmp_path):
    """queue_failed_action should move the file to vault/Quarantine/."""
    vault = tmp_path
    (vault / "Needs_Action").mkdir()
    action = vault / "Needs_Action" / "email-test.md"
    action.write_text("---\ntype: email\n---\n# Test", encoding="utf-8")

    queue_failed_action(vault, action, "API timeout")

    assert not action.exists()
    assert (vault / "Quarantine" / "email-test.md").exists()


def test_queue_failed_action_adds_error_metadata(tmp_path):
    """queue_failed_action should add error info to the file's frontmatter."""
    vault = tmp_path
    (vault / "Needs_Action").mkdir()
    action = vault / "Needs_Action" / "email-test.md"
    action.write_text("---\ntype: email\n---\n# Test", encoding="utf-8")

    queue_failed_action(vault, action, "API timeout")

    quarantined = vault / "Quarantine" / "email-test.md"
    content = quarantined.read_text(encoding="utf-8")
    assert "quarantine_error: API timeout" in content
    assert "quarantine_time:" in content


# ---------------------------------------------------------------------------
# process_quarantine tests
# ---------------------------------------------------------------------------

def test_process_quarantine_moves_old_items_back(tmp_path):
    """process_quarantine should move items older than threshold back to Needs_Action/."""
    vault = tmp_path
    (vault / "Needs_Action").mkdir()
    (vault / "Quarantine").mkdir()

    # Create a quarantined file with an old timestamp
    quarantined = vault / "Quarantine" / "email-old.md"
    quarantined.write_text(
        "---\ntype: email\nquarantine_error: API timeout\nquarantine_time: 2020-01-01T00:00:00Z\n---\n# Old item",
        encoding="utf-8",
    )

    moved = process_quarantine(vault)

    assert len(moved) == 1
    assert not quarantined.exists()
    restored = vault / "Needs_Action" / "email-old.md"
    assert restored.exists()
    # Quarantine metadata should be removed from restored file
    content = restored.read_text(encoding="utf-8")
    assert "quarantine_error" not in content
    assert "quarantine_time" not in content


def test_process_quarantine_skips_recent_items(tmp_path):
    """process_quarantine should NOT move items quarantined very recently."""
    vault = tmp_path
    (vault / "Needs_Action").mkdir()
    (vault / "Quarantine").mkdir()

    # Create a quarantined file with a very recent timestamp (now)
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    quarantined = vault / "Quarantine" / "email-new.md"
    quarantined.write_text(
        f"---\ntype: email\nquarantine_error: API timeout\nquarantine_time: {now}\n---\n# New item",
        encoding="utf-8",
    )

    moved = process_quarantine(vault, min_age_seconds=300)

    assert len(moved) == 0
    assert quarantined.exists()


def test_process_quarantine_handles_empty_quarantine(tmp_path):
    """process_quarantine should return empty list when no Quarantine/ folder exists."""
    vault = tmp_path
    (vault / "Needs_Action").mkdir()

    moved = process_quarantine(vault)
    assert moved == []
