"""Ralph Wiggum loop -- autonomous multi-step task completion.

Keeps Claude iterating on a task until:
1. Claude outputs <promise>TASK_COMPLETE</promise> (promise-based)
2. The task file moves to /Done (file-movement-based)
3. Max iterations reached (safety limit)

Named after the Claude Code plugin pattern described in the hackathon
documentation.  The loop feeds Claude's previous output back as context
on each iteration, building up incremental progress toward a goal.
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Promise tag pattern ────────────────────────────────────────────────

_PROMISE_PATTERN = re.compile(r"<promise>TASK_COMPLETE</promise>")


def check_promise_completion(output: str) -> bool:
    """Check if Claude's output contains <promise>TASK_COMPLETE</promise>.

    Args:
        output: The raw text output from Claude.

    Returns:
        True if the exact promise tag is found, False otherwise.
    """
    return bool(_PROMISE_PATTERN.search(output))


# ── File-movement check ───────────────────────────────────────────────


def check_file_completion(task_file: Path, done_dir: Path) -> bool:
    """Check if *task_file* has been moved to *done_dir*.

    The comparison is by filename only -- if a file with the same name
    exists inside *done_dir*, the task is considered complete.

    Args:
        task_file: Original path of the task file.
        done_dir:  Path to the Done/ directory.

    Returns:
        True if *task_file.name* exists in *done_dir*.
    """
    return (done_dir / task_file.name).exists()


# ── Task state management ─────────────────────────────────────────────


def create_task_state(
    vault_path: Path,
    task_prompt: str,
    iteration: int = 0,
    previous_output: str = "",
) -> Path:
    """Create or update a state file in the vault for tracking loop progress.

    The state file is written to ``vault_path/Logs/ralph-wiggum-state.json``
    so that it can be inspected during or after a run.

    Args:
        vault_path:      Root of the Obsidian vault.
        task_prompt:      The original task prompt.
        iteration:        Current iteration number (0-indexed at creation).
        previous_output:  Output from the previous Claude invocation.

    Returns:
        Path to the written state file.
    """
    state = {
        "task_prompt": task_prompt,
        "iteration": iteration,
        "previous_output": previous_output,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    state_path = vault_path / "Logs" / "ralph-wiggum-state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return state_path


# ── Core loop ──────────────────────────────────────────────────────────


def _invoke_claude(prompt: str, claude_model: str) -> str:
    """Invoke Claude via ``claude --print`` subprocess.

    Args:
        prompt:       The full prompt text to send.
        claude_model: The model identifier (e.g. ``claude-sonnet-4-5-20250929``).

    Returns:
        Claude's stdout response text.
    """
    result = subprocess.run(
        ["claude", "--print", "--model", claude_model, prompt],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        logger.warning("Claude returned non-zero exit code %d", result.returncode)
    return result.stdout


def run_ralph_loop(
    vault_path: Path,
    task_prompt: str,
    claude_model: str = "claude-sonnet-4-5-20250929",
    max_iterations: int = 10,
    completion_strategy: str = "promise",
    task_file: Path | None = None,
) -> dict:
    """Run a Ralph Wiggum loop until task completion or max iterations.

    Args:
        vault_path:          Root of the Obsidian vault.
        task_prompt:         The task description / prompt.
        claude_model:        Claude model to invoke.
        max_iterations:      Safety limit on number of iterations.
        completion_strategy: ``"promise"`` or ``"file_movement"``.
        task_file:           Required when *completion_strategy* is
                             ``"file_movement"``; path to the task file
                             that should end up in ``Done/``.

    Returns:
        A dict with keys:
            - **completed** (bool): Whether the task finished.
            - **iterations** (int): Number of iterations executed.
            - **strategy** (str): The completion strategy used.
            - **output** (str): The last Claude response.
    """
    if completion_strategy == "file_movement" and task_file is None:
        raise ValueError("task_file is required for file_movement strategy")

    done_dir = vault_path / "Done"
    iteration_logs: list[dict] = []
    last_output = ""

    for i in range(1, max_iterations + 1):
        # Build prompt -- on subsequent iterations, include previous output
        if i == 1:
            prompt = task_prompt
        else:
            prompt = (
                f"Continue the following task.  Here is your previous output:\n\n"
                f"---\n{last_output}\n---\n\n"
                f"Original task: {task_prompt}\n\n"
                f"Iteration {i} of {max_iterations}. "
                f"When complete, output <promise>TASK_COMPLETE</promise>."
            )

        # Persist state before invocation
        create_task_state(vault_path, task_prompt, iteration=i, previous_output=last_output)

        logger.info("Ralph Wiggum loop iteration %d/%d", i, max_iterations)
        last_output = _invoke_claude(prompt, claude_model)

        # Record iteration log entry
        iteration_logs.append({
            "iteration": i,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prompt_length": len(prompt),
            "output_length": len(last_output),
            "output_preview": last_output[:200],
        })

        # Check completion condition
        completed = False
        if completion_strategy == "promise":
            completed = check_promise_completion(last_output)
        elif completion_strategy == "file_movement":
            completed = check_file_completion(task_file, done_dir)

        if completed:
            logger.info("Ralph Wiggum loop completed at iteration %d", i)
            _write_iteration_log(vault_path, iteration_logs)
            return {
                "completed": True,
                "iterations": i,
                "strategy": completion_strategy,
                "output": last_output,
            }

    # Max iterations reached without completion
    logger.warning("Ralph Wiggum loop hit max iterations (%d)", max_iterations)
    _write_iteration_log(vault_path, iteration_logs)
    return {
        "completed": False,
        "iterations": max_iterations,
        "strategy": completion_strategy,
        "output": last_output,
    }


def _write_iteration_log(vault_path: Path, entries: list[dict]) -> Path:
    """Write iteration log entries to ``vault_path/Logs/ralph-wiggum-<ts>.json``.

    Returns:
        Path to the written log file.
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = vault_path / "Logs" / f"ralph-wiggum-{ts}.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    return log_path
