---
id: 5
title: Add parse_frontmatter and extract_reply_block to utils
stage: green
date: 2026-02-16
surface: agent
model: claude-opus-4-6
feature: digital-fte-silver
branch: feature/digital-fte-silver
user: user
command: task-2-implementation
labels: ["utils", "parse-frontmatter", "extract-reply-block", "tdd", "silver-tier"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - src/utils.py
  - tests/test_utils.py
tests:
  - tests/test_utils.py::test_parse_frontmatter_extracts_yaml
  - tests/test_utils.py::test_parse_frontmatter_returns_empty_on_no_frontmatter
  - tests/test_utils.py::test_extract_reply_block
  - tests/test_utils.py::test_extract_reply_block_returns_none_when_missing
---

## Prompt

You are implementing Task 2: Add `parse_frontmatter()` and `extract_reply_block()` to utils

## Task Description

**Files:**
- Modify: `tests/test_utils.py`
- Modify: `src/utils.py`

Follow TDD to add two utility functions: parse_frontmatter() for extracting YAML frontmatter from markdown files, and extract_reply_block() for extracting reply text between ---BEGIN REPLY--- / ---END REPLY--- markers. Write failing tests first, then implement, then verify pass, then commit.

## Response snapshot

Implemented Task 2 following TDD (Red-Green):

1. RED: Added four tests to `tests/test_utils.py`:
   - `test_parse_frontmatter_extracts_yaml` -- verifies YAML extraction between --- delimiters
   - `test_parse_frontmatter_returns_empty_on_no_frontmatter` -- verifies empty dict when no YAML block
   - `test_extract_reply_block` -- verifies text extraction between BEGIN/END REPLY markers
   - `test_extract_reply_block_returns_none_when_missing` -- verifies None when no markers
   Verified all 4 fail with `ImportError: cannot import name`.

2. GREEN: Added `import yaml` at top of `src/utils.py`. Implemented `parse_frontmatter()` using `text.split("---", 2)` + `yaml.safe_load()` with error handling. Implemented `extract_reply_block()` using `str.find()` for BEGIN/END markers with `.strip()`.

3. Fixed test data: quoted `subject: "Re: Hello"` in YAML frontmatter test since `Re: Hello` (colon+space) is invalid unquoted YAML.

4. All 7 tests pass (3 existing + 4 new), zero regressions.

5. Committed as `feat: add parse_frontmatter and extract_reply_block helpers` on `feature/digital-fte-silver`.

## Outcome

- Impact: Added two utility functions needed by the Silver tier orchestrator for parsing plan files
- Tests: 4 new tests added, all 7 utils tests pass
- Files: 2 files modified (src/utils.py, tests/test_utils.py)
- Next prompts: Task 3 - Add gmail.send scope to auth
- Reflection: Clean TDD cycle; discovered YAML quoting issue in test spec data and fixed it

## Evaluation notes (flywheel)

- Failure modes observed: Test spec contained unquoted YAML value with colon (subject: Re: Hello) which is invalid YAML; fixed by quoting
- Graders run and results (PASS/FAIL): pytest tests/test_utils.py PASS (7/7)
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): null
