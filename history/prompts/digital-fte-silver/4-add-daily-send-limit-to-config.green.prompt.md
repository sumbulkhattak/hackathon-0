---
id: 4
title: Add daily_send_limit to Config
stage: green
date: 2026-02-16
surface: agent
model: claude-opus-4-6
feature: digital-fte-silver
branch: feature/digital-fte-silver
user: user
command: task-1-implementation
labels: ["config", "daily-send-limit", "tdd", "silver-tier"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - src/config.py
  - tests/test_config.py
  - .env.example
tests:
  - tests/test_config.py::test_config_loads_daily_send_limit
  - tests/test_config.py::test_config_daily_send_limit_default
---

## Prompt

You are implementing Task 1: Add `daily_send_limit` to Config

## Task Description

**Files:**
- Modify: `tests/test_config.py`
- Modify: `src/config.py`
- Modify: `.env.example`

**Step 1: Write the failing test**

Add to `tests/test_config.py`:

```python
def test_config_loads_daily_send_limit(monkeypatch):
    """Config should read DAILY_SEND_LIMIT from environment."""
    monkeypatch.setenv("DAILY_SEND_LIMIT", "50")
    from src.config import load_config
    cfg = load_config()
    assert cfg.daily_send_limit == 50


def test_config_daily_send_limit_default(monkeypatch):
    """Config should default daily_send_limit to 20."""
    monkeypatch.delenv("DAILY_SEND_LIMIT", raising=False)
    from src.config import load_config
    cfg = load_config()
    assert cfg.daily_send_limit == 20
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config.py -v`
Expected: FAIL -- `Config` has no `daily_send_limit` field

**Step 3: Implement the config change**

In `src/config.py`, add `daily_send_limit: int` to the `Config` dataclass and load it in `load_config()`.

In `.env.example`, append DAILY_SEND_LIMIT=20.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: ALL PASS

**Step 5: Commit**

## Response snapshot

Implemented Task 1 following TDD (Red-Green):

1. RED: Added two tests to `tests/test_config.py` -- `test_config_loads_daily_send_limit` (reads env var "50" -> 50) and `test_config_daily_send_limit_default` (defaults to 20). Verified both fail with `AttributeError: 'Config' object has no attribute 'daily_send_limit'`.

2. GREEN: Added `daily_send_limit: int` field to Config dataclass in `src/config.py`. Added `daily_send_limit=int(os.getenv("DAILY_SEND_LIMIT", "20"))` to `load_config()`. Added env var documentation to `.env.example`.

3. All 22 tests pass (5 config + 17 existing), zero regressions.

4. Committed as `feat: add daily_send_limit to config` on `feature/digital-fte-silver`.

## Outcome

- Impact: Added daily_send_limit config field for Silver tier email sending cap
- Tests: 2 new tests added, all 22 tests pass
- Files: 3 files modified (src/config.py, tests/test_config.py, .env.example)
- Next prompts: Task 2 - Add parse_frontmatter and extract_reply_block to utils
- Reflection: Clean TDD cycle, minimal diff, no regressions

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): pytest full suite PASS (22/22)
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): null
