---
id: 14
title: Add error recovery with retry and quarantine
stage: green
date: 2026-02-17
surface: agent
model: claude-opus-4-6
feature: digital-fte-gold
branch: feature/digital-fte-gold-tier
user: human
command: implement error recovery
labels: ["error-recovery", "retry", "quarantine", "graceful-degradation", "gold-tier"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - src/retry.py
  - tests/test_retry.py
  - skills/error-recovery.md
  - setup_vault.py
tests:
  - tests/test_retry.py::test_with_retry_succeeds_first_try
  - tests/test_retry.py::test_with_retry_succeeds_after_transient_error
  - tests/test_retry.py::test_with_retry_gives_up_after_max_attempts
  - tests/test_retry.py::test_with_retry_does_not_retry_permanent_error
  - tests/test_retry.py::test_with_retry_exponential_backoff_delays
  - tests/test_retry.py::test_with_retry_caps_delay_at_max
  - tests/test_retry.py::test_with_retry_calls_on_failure_callback
  - tests/test_retry.py::test_queue_failed_action_creates_quarantine_dir
  - tests/test_retry.py::test_queue_failed_action_moves_file
  - tests/test_retry.py::test_queue_failed_action_adds_error_metadata
  - tests/test_retry.py::test_process_quarantine_moves_old_items_back
  - tests/test_retry.py::test_process_quarantine_skips_recent_items
  - tests/test_retry.py::test_process_quarantine_handles_empty_quarantine
---

## Prompt

You are implementing error recovery and graceful degradation for the Digital FTE project at C:\Users\LAPTOP WORLD\Desktop\hackathon-0.

## Context
Gold tier requires "Error recovery and graceful degradation" including:
- Exponential backoff retry for transient errors
- Queue locally when APIs are down
- Never auto-retry payments
- Watchers continue collecting when Claude is unavailable

## What to Build

### 1. Create `src/retry.py`

```python
"""Retry logic with exponential backoff and graceful degradation."""
import time
import logging
from functools import wraps

logger = logging.getLogger("digital_fte.retry")

class TransientError(Exception):
    """Errors that may resolve on retry (network, API rate limit, timeout)."""
    pass

class PermanentError(Exception):
    """Errors that won't resolve on retry (auth revoked, bad data)."""
    pass

def with_retry(max_attempts=3, base_delay=1, max_delay=60, on_failure=None):
    """Decorator for exponential backoff retry on TransientError."""

def queue_failed_action(vault_path, action_file, error_msg):
    """Move a failed action to a quarantine queue for later retry."""

def process_quarantine(vault_path):
    """Check quarantined items and move recoverable ones back to Needs_Action/."""
```

### 2. Create `tests/test_retry.py` with 11+ TDD tests
### 3. Create `skills/error-recovery.md` Agent Skill
### 4. Add "Quarantine" folder to setup_vault.py VAULT_FOLDERS
### 5. Run tests and commit

## Response snapshot

Implemented error recovery and graceful degradation following TDD:

1. Created `tests/test_retry.py` with 13 tests covering all retry, quarantine, and graceful degradation scenarios.
2. Confirmed all tests failed (RED phase) before implementation.
3. Created `src/retry.py` with:
   - `TransientError` and `PermanentError` exception classes
   - `with_retry()` decorator with exponential backoff (base_delay * 2^attempt, capped at max_delay)
   - `queue_failed_action()` to move failed actions to vault/Quarantine/ with error metadata in frontmatter
   - `process_quarantine()` to restore old quarantined items back to Needs_Action/ after min_age_seconds
4. All 13 tests passed (GREEN phase).
5. Created `skills/error-recovery.md` documenting the skill.
6. Added "Quarantine" to VAULT_FOLDERS in setup_vault.py.
7. Full test suite: 201 passed.
8. Committed as `dacfc3f`.

## Outcome

- Impact: Gold tier error recovery requirement fulfilled; system now handles transient failures gracefully
- Tests: 13 new tests, all passing; 201 total tests passing
- Files: 4 files changed (src/retry.py, tests/test_retry.py, skills/error-recovery.md, setup_vault.py)
- Next prompts: Integrate with_retry into orchestrator and watcher API calls; add payment safety guard
- Reflection: Clean TDD cycle; tests written first then implementation to make them pass

## Evaluation notes (flywheel)

- Failure modes observed: None; clean implementation cycle
- Graders run and results (PASS/FAIL): pytest PASS (13/13 new, 201/201 total)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Wire with_retry into orchestrator._invoke_claude and gmail_sender.send_reply
