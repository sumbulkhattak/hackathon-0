---
id: 1
title: classify priority urgency keywords
stage: green
date: 2026-02-17
surface: agent
model: claude-opus-4-6
feature: digital-fte-obsidian
branch: feature/digital-fte-obsidian
user: user
command: task-1-implementation
labels: ["priority", "classify", "urgency", "tdd", "obsidian"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - src/priority.py
  - tests/test_priority.py
tests:
  - tests/test_priority.py::test_classify_high_on_urgency_keyword_in_subject
  - tests/test_priority.py::test_classify_high_on_urgency_keyword_in_body
  - tests/test_priority.py::test_classify_high_is_case_insensitive
  - tests/test_priority.py::test_classify_normal_without_keywords
---

## Prompt

You are implementing Task 1 of the Obsidian tier for the Digital FTE project. Task 1: Create `classify_priority()` with urgency keyword detection. Follow strict TDD: RED -> verify fail -> GREEN -> verify pass -> COMMIT. Create test file tests/test_priority.py with 4 tests, then create src/priority.py with the implementation.

## Response snapshot

Implemented Task 1 following strict TDD:
1. RED: Created tests/test_priority.py with 4 tests. Ran pytest - confirmed ModuleNotFoundError (tests fail).
2. GREEN: Created src/priority.py with classify_priority() function that checks URGENCY_KEYWORDS (urgent, asap, deadline, overdue) case-insensitively in subject and body. Ran pytest - all 4 tests pass.
3. COMMIT: Committed with message "feat: add classify_priority with urgency keyword detection".

## Outcome

- Impact: New priority classification module added to the project
- Tests: 4/4 passing (test_priority.py)
- Files: 2 created (src/priority.py, tests/test_priority.py)
- Next prompts: Task 2 - VIP sender detection
- Reflection: Clean TDD cycle completed successfully

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): pytest PASS (4/4)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Add VIP sender detection to classify_priority
