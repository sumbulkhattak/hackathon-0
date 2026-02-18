---
id: 13
title: Add Ralph Wiggum Loop for Autonomous Task Completion
stage: green
date: 2026-02-17
surface: agent
model: claude-opus-4-6
feature: digital-fte-gold
branch: feature/digital-fte-gold-tier
user: developer
command: implementation
labels: ["ralph-wiggum", "autonomous-loop", "gold-tier", "tdd"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - src/ralph_wiggum.py
  - tests/test_ralph_wiggum.py
  - skills/ralph-wiggum.md
  - setup_vault.py
tests:
  - tests/test_ralph_wiggum.py::test_check_promise_completion_found
  - tests/test_ralph_wiggum.py::test_check_promise_completion_not_found
  - tests/test_ralph_wiggum.py::test_check_promise_completion_partial_tag
  - tests/test_ralph_wiggum.py::test_check_file_completion_file_in_done
  - tests/test_ralph_wiggum.py::test_check_file_completion_file_not_in_done
  - tests/test_ralph_wiggum.py::test_create_task_state_creates_file
  - tests/test_ralph_wiggum.py::test_create_task_state_includes_iteration
  - tests/test_ralph_wiggum.py::test_run_ralph_loop_completes_on_promise
  - tests/test_ralph_wiggum.py::test_run_ralph_loop_stops_at_max_iterations
  - tests/test_ralph_wiggum.py::test_run_ralph_loop_file_movement_strategy
  - tests/test_ralph_wiggum.py::test_run_ralph_loop_returns_result_dict
  - tests/test_ralph_wiggum.py::test_run_ralph_loop_logs_iterations
---

## Prompt

You are implementing the "Ralph Wiggum loop" for the Digital FTE project. Build src/ralph_wiggum.py with run_ralph_loop(), check_promise_completion(), check_file_completion(), create_task_state(). Two completion strategies: promise-based (<promise>TASK_COMPLETE</promise>) and file-movement-based. Write 12 TDD tests, create skills/ralph-wiggum.md Agent Skill, add Briefings/ folder to setup_vault.py VAULT_FOLDERS. Follow TDD strictly: write failing tests first, then implement.

## Response snapshot

Implemented the Ralph Wiggum autonomous loop module following strict TDD:

1. Wrote 12 failing tests in tests/test_ralph_wiggum.py covering: promise completion detection (found/not found/partial tag), file movement detection (in Done/not in Done), task state creation (file creation/iteration tracking), and full loop behavior (promise completion, max iterations, file movement strategy, result dict structure, iteration logging).

2. Implemented src/ralph_wiggum.py with: check_promise_completion() using regex for exact <promise>TASK_COMPLETE</promise> matching; check_file_completion() checking by filename in Done/ dir; create_task_state() writing JSON state to vault/Logs/; run_ralph_loop() with iterative Claude invocation, context chaining, and two completion strategies; _write_iteration_log() for per-run log files.

3. Created skills/ralph-wiggum.md documenting both strategies, return value format, safety limits, and utility functions.

4. Added "Briefings" to VAULT_FOLDERS in setup_vault.py.

All 188 tests pass (12 new + 176 existing).

## Outcome

- Impact: Added autonomous multi-step task completion capability (Gold tier feature)
- Tests: 12 new tests, all passing. 188 total tests passing.
- Files: 4 files created/modified (src/ralph_wiggum.py, tests/test_ralph_wiggum.py, skills/ralph-wiggum.md, setup_vault.py)
- Next prompts: Integrate Ralph Wiggum loop with orchestrator, implement error recovery, build CEO Briefing generator
- Reflection: Clean TDD flow -- all 12 tests failed on first run (ModuleNotFoundError), then all passed after implementation. Promise-based strategy is simple and reliable; file-movement strategy requires careful mock setup.

## Evaluation notes (flywheel)

- Failure modes observed: None -- all tests passed on first green implementation
- Graders run and results (PASS/FAIL): pytest 12/12 PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Add retry/backoff on Claude subprocess failures in the loop
