---
id: 7
title: Extend Orchestrator with Reply Execution
stage: green
date: 2026-02-16
surface: agent
model: claude-opus-4-6
feature: digital-fte-silver
branch: feature/digital-fte-silver
user: user
command: task-5-orchestrator-reply
labels: ["orchestrator", "gmail", "reply", "tdd", "silver-tier"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - src/orchestrator.py
  - tests/test_orchestrator.py
  - src/gmail_sender.py
tests:
  - tests/test_orchestrator.py::test_orchestrator_sends_reply_on_approved
  - tests/test_orchestrator.py::test_orchestrator_skips_send_when_no_action
  - tests/test_orchestrator.py::test_orchestrator_respects_daily_send_limit
  - tests/test_orchestrator.py::test_orchestrator_handles_missing_reply_block
---

## Prompt

You are implementing Task 5: Extend Orchestrator with reply execution

## Task Description

**Files:**
- Modify: `tests/test_orchestrator.py`
- Modify: `src/orchestrator.py`

Follow TDD to add Gmail reply execution to the orchestrator: add tests, verify they fail, implement, verify they pass, commit.

## Response snapshot

Extended the Orchestrator class to support Gmail reply execution via TDD:

1. Added 4 new tests and a helper function `make_reply_plan()` to `tests/test_orchestrator.py`
2. Rewrote `src/orchestrator.py` to:
   - Accept `gmail_service` and `daily_send_limit` parameters (with backward-compatible defaults)
   - Import `send_reply`, `check_send_limit`, `increment_send_count` from `gmail_sender`
   - Import `parse_frontmatter`, `extract_reply_block` from `utils`
   - `execute_approved()` now: parses frontmatter for `action: reply`, checks daily send limit, extracts reply block, sends via Gmail API, handles errors
   - `process_action()` now: detects reply blocks in Claude output and auto-populates reply frontmatter fields
3. Fixed `check_send_limit()` edge case: `limit=0` with no count file now correctly returns `False` (was `True`)
4. All 36 tests pass (7 orchestrator + 29 others)

## Outcome

- Impact: Core orchestrator now handles full reply execution pipeline with safety limits
- Tests: 7/7 orchestrator tests pass, 36/36 full suite
- Files: 3 modified (src/orchestrator.py, tests/test_orchestrator.py, src/gmail_sender.py)
- Next prompts: Task 6 - Wire Gmail service into main.py
- Reflection: Edge case in check_send_limit with limit=0 required a fix; TDD caught it

## Evaluation notes (flywheel)

- Failure modes observed: check_send_limit returned True for limit=0 when no count file existed
- Graders run and results (PASS/FAIL): pytest 36/36 PASS
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): null
