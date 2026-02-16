---
id: 3
title: Vault Watchers Auth Implementation
stage: green
date: 2026-02-16
surface: agent
model: claude-opus-4-6
feature: digital-fte-bronze
branch: feature/digital-fte-bronze
user: user
command: implement tasks 4-7
labels: ["vault", "watchers", "gmail", "auth", "implementation"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - setup_vault.py
  - tests/test_setup_vault.py
  - src/watchers/base_watcher.py
  - tests/watchers/test_base_watcher.py
  - src/watchers/gmail_watcher.py
  - tests/watchers/test_gmail_watcher.py
  - src/auth.py
  - credentials/.gitkeep
tests:
  - tests/test_setup_vault.py::test_setup_vault_creates_all_folders
  - tests/test_setup_vault.py::test_setup_vault_creates_handbook
  - tests/test_setup_vault.py::test_setup_vault_is_idempotent
  - tests/watchers/test_base_watcher.py::test_base_watcher_is_abstract
  - tests/watchers/test_base_watcher.py::test_concrete_watcher_creates_action_files
  - tests/watchers/test_base_watcher.py::test_run_single_cycle
  - tests/watchers/test_gmail_watcher.py::test_gmail_watcher_check_for_updates_returns_messages
  - tests/watchers/test_gmail_watcher.py::test_gmail_watcher_check_no_messages
  - tests/watchers/test_gmail_watcher.py::test_gmail_watcher_creates_action_file
  - tests/watchers/test_gmail_watcher.py::test_gmail_watcher_marks_as_processed
---

## Prompt

You are implementing Tasks 4, 5, 6, and 7 SEQUENTIALLY for the Digital FTE Bronze project.

Working directory: C:\Users\LAPTOP WORLD\Desktop\hackathon-0
Branch: feature/digital-fte-bronze

IMPORTANT: Do each task one at a time. Write files, run tests, commit, then move to the next task.

TASK 4: Vault Initialization - setup_vault.py with folder structure and handbook
TASK 5: Base Watcher Abstract Class - BaseWatcher ABC with run_once cycle
TASK 6: Gmail Watcher - GmailWatcher with polling, action files, label tracking
TASK 7: Gmail Authentication Helper - OAuth 2.0 helper for Gmail API

## Response snapshot

Implemented all 4 tasks sequentially with RED-GREEN cycle for each:
- Task 4: Created setup_vault.py and tests (3 tests pass) - commit ea20bb4
- Task 5: Created BaseWatcher ABC and tests (3 tests pass) - commit ffb52ad
- Task 6: Created GmailWatcher and tests (4 tests pass) - commit dde90fc
- Task 7: Created auth.py and credentials/.gitkeep - commit 0ba4af2
Final verification: 16/16 tests passing across the entire test suite.

## Outcome

- Impact: Core vault initialization, watcher architecture, Gmail integration, and auth helper implemented
- Tests: 16 passed, 0 failed (10 new tests added across 3 test files)
- Files: 8 files created (4 source, 3 test, 1 gitkeep)
- Next prompts: Implement remaining tasks (Claude processor, approval workflow, main orchestrator)
- Reflection: Clean sequential implementation with proper RED-GREEN test cycles for each task

## Evaluation notes (flywheel)

- Failure modes observed: credentials/ dir was gitignored requiring force-add for .gitkeep
- Graders run and results (PASS/FAIL): All 16 tests PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A
