# Skill: Ralph Wiggum Loop

## Description
Autonomous multi-step task completion loop. Keeps Claude iterating on a task
until it signals completion or a safety limit is reached.

Named after the Claude Code plugin pattern: give Claude a task, let it run in
a loop, and detect when it is done.

## Completion Strategies

### Promise-Based (default)
Claude outputs `<promise>TASK_COMPLETE</promise>` when the task is finished.

```python
from src.ralph_wiggum import run_ralph_loop
result = run_ralph_loop(
    vault_path=vault,
    task_prompt="Triage all Inbox emails and move them to Needs_Action",
    max_iterations=10,
    completion_strategy="promise",
)
```

### File-Movement-Based
The loop watches for a specific task file to appear in the `Done/` folder.

```python
from src.ralph_wiggum import run_ralph_loop
result = run_ralph_loop(
    vault_path=vault,
    task_prompt="Process email-abc123.md through full pipeline",
    max_iterations=10,
    completion_strategy="file_movement",
    task_file=vault / "Needs_Action" / "email-abc123.md",
)
```

## Return Value

```python
{
    "completed": True,       # Whether the task finished
    "iterations": 3,         # Number of loop iterations executed
    "strategy": "promise",   # Which strategy was used
    "output": "...",         # Last Claude response
}
```

## Safety Limits
- `max_iterations` (default 10) prevents runaway loops.
- Each iteration is logged to `vault/Logs/ralph-wiggum-<timestamp>.json`.
- A state file at `vault/Logs/ralph-wiggum-state.json` tracks progress.

## Utility Functions

| Function | Purpose |
|---|---|
| `check_promise_completion(output)` | Returns True if output contains the TASK_COMPLETE promise tag |
| `check_file_completion(task_file, done_dir)` | Returns True if task file name exists in Done/ |
| `create_task_state(vault_path, prompt, iteration, previous_output)` | Writes/updates loop state file |

## Implementation
- Module: `src/ralph_wiggum.py`
- Tests: `tests/test_ralph_wiggum.py` (12 tests)
