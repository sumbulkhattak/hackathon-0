---
id: 11
title: Add extract_confidence utility
stage: green
date: 2026-02-16
surface: agent
model: claude-opus-4-6
feature: digital-fte-platinum
branch: feature/digital-fte-platinum
user: developer
command: task-1-extract-confidence
labels: ["utils", "confidence", "tdd", "platinum"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - src/utils.py
  - tests/test_utils.py
tests:
  - test_extract_confidence_parses_valid_score
  - test_extract_confidence_returns_zero_when_missing
  - test_extract_confidence_returns_zero_for_invalid_value
---

## Prompt

You are implementing Task 1 of the Digital FTE Platinum tier plan. Follow TDD strictly.

## Context
Project: Digital FTE — an autonomous AI agent using an Obsidian vault pipeline.
Branch: `feature/digital-fte-platinum`
Working directory: `C:\Users\LAPTOP WORLD\Desktop\hackathon-0`

## Task: Add `extract_confidence()` utility function

### Files to modify:
- `tests/test_utils.py` — add 3 tests
- `src/utils.py` — add `extract_confidence()` function

### Step 1: Write failing tests

Add these 3 tests to the END of `tests/test_utils.py`:

```python
def test_extract_confidence_parses_valid_score():
    """extract_confidence should parse a float from ## Confidence section."""
    from src.utils import extract_confidence
    response = "## Analysis\nSome analysis.\n\n## Confidence\n0.85\n\n## Recommended Actions\n1. Reply"
    assert extract_confidence(response) == 0.85


def test_extract_confidence_returns_zero_when_missing():
    """extract_confidence should return 0.0 when ## Confidence section is absent."""
    from src.utils import extract_confidence
    response = "## Analysis\nSome analysis.\n\n## Recommended Actions\n1. Reply"
    assert extract_confidence(response) == 0.0


def test_extract_confidence_returns_zero_for_invalid_value():
    """extract_confidence should return 0.0 when confidence value is not a number."""
    from src.utils import extract_confidence
    response = "## Analysis\nSome analysis.\n\n## Confidence\nhigh\n\n## Recommended Actions\n1. Reply"
    assert extract_confidence(response) == 0.0
```

### Step 2: Run tests to verify they fail

Run: `pytest tests/test_utils.py -k "extract_confidence" -v`

### Step 3: Implement `extract_confidence()`

Add to the END of `src/utils.py`:

```python
def extract_confidence(response: str) -> float:
    """Extract confidence score from Claude's ## Confidence section.

    Returns 0.0 if the section is missing or the value is not a valid float.
    """
    marker = "## Confidence"
    idx = response.find(marker)
    if idx == -1:
        return 0.0
    after = response[idx + len(marker):]
    for line in after.split("\n"):
        line = line.strip()
        if line:
            try:
                return float(line)
            except ValueError:
                return 0.0
    return 0.0
```

### Step 4: Run tests to verify they pass

Run: `pytest tests/test_utils.py -v`

### Step 5: Commit

```bash
git add tests/test_utils.py src/utils.py
git commit -m "feat: add extract_confidence utility for parsing Claude confidence scores"
```

IMPORTANT: Follow TDD exactly. Write tests first, verify they fail, implement, verify they pass, commit.

## Response snapshot

Implemented Task 1 following strict TDD:
1. Added 3 failing tests to tests/test_utils.py (red phase confirmed: ImportError for all 3)
2. Implemented extract_confidence() in src/utils.py
3. All 10 tests pass (green phase confirmed)
4. Committed as: feat: add extract_confidence utility for parsing Claude confidence scores (91f4322)

## Outcome

- Impact: Added extract_confidence() utility that parses float confidence scores from Claude's ## Confidence markdown section, returning 0.0 for missing or invalid values.
- Tests: 3 new tests added, all passing (10/10 total in test_utils.py)
- Files: src/utils.py (added function), tests/test_utils.py (added 3 tests)
- Next prompts: Task 2 - Add auto_approve_threshold to Config
- Reflection: Clean TDD cycle; function is simple string parsing with good edge case coverage.

## Evaluation notes (flywheel)

- Failure modes observed: None; clean red-green cycle.
- Graders run and results (PASS/FAIL): pytest 10/10 PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A
