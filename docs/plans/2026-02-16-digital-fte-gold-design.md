# Digital FTE — Gold Tier Design

**Date:** 2026-02-16
**Tier:** Gold
**Approach:** Extend Orchestrator (Approach A — no separate ReviewAgent class)

## Summary

Add self-review loops ("Ralph Wiggum loops") so the agent learns from rejected plans. When a human rejects a plan by moving it to `vault/Rejected/`, the agent analyzes what went wrong, extracts a learning, and stores it in `vault/Agent_Memory.md`. Future plans are influenced by accumulated learnings.

## Scope

- **In scope:** Rejected/ folder, review_rejected() method, Agent_Memory.md, Claude prompt updated to read memory, immediate per-rejection learning
- **Out of scope:** Edit-diff detection, reply quality scoring, periodic batch reviews, autonomous triage, auto-approve

## Decisions

- **Feedback channel:** New `vault/Rejected/` folder — human moves bad plans there instead of to Approved/
- **Memory storage:** `vault/Agent_Memory.md` — single markdown file, human-reviewable and editable
- **Review trigger:** Immediate — each main loop iteration checks Rejected/ for new files
- **Learning format:** Timestamped bullet points appended to Agent_Memory.md
- **Architecture:** Extend Orchestrator with `review_rejected()` method (no new classes)

## Feedback Flow

```
Pending_Approval/
       │
  Human rejects ──► Rejected/
                       │
              Orchestrator.review_rejected()
                       │
              Claude analyzes: "Why was this rejected?"
                       │
              Appends learning to Agent_Memory.md
                       │
              Moves to Done/ (status: rejected_reviewed)
```

## Agent Memory File

Created by `setup_vault.py` with starter template:

```markdown
# Agent Memory

Learnings from past decisions. This file is read by Claude alongside the Company Handbook when generating plans.

## Patterns
<!-- New learnings are appended here automatically -->
```

Each learning appended as:

```markdown
- **2026-02-16T14:30:00Z** — Rejected plan for "Invoice #99": Don't offer payment timeline commitments without checking accounting first. Stick to acknowledging receipt only.
```

## Claude Integration

### Review Prompt (for analyzing rejections)

```
You are reviewing a rejected plan. The human moved this plan to Rejected/
instead of approving it. Analyze what went wrong and produce ONE concise
learning (1-2 sentences) that should guide future plans.

## The Rejected Plan
[full plan content]

## Current Agent Memory
[current Agent_Memory.md content]

Respond with ONLY the learning text, no markdown headers or formatting.
```

### Updated Plan Generation Prompt

The existing `_invoke_claude()` method is updated to include `Agent_Memory.md` content alongside the Company Handbook under a `## Agent Memory` section. If the file doesn't exist or is empty, it's omitted.

## Orchestrator Changes

### New method: `review_rejected(rejected_file)`

1. Read rejected plan content
2. Read current Agent_Memory.md
3. Invoke Claude with review prompt
4. Append timestamped learning to Agent_Memory.md
5. Move rejected file to Done/ with status: rejected_reviewed
6. Log the action

### New method: `get_rejected_actions()`

```python
def get_rejected_actions(self) -> list[Path]:
    return sorted(self.rejected.glob("*.md"))
```

### Main loop addition

```python
for rejected_file in orchestrator.get_rejected_actions():
    orchestrator.review_rejected(rejected_file)
```

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Claude fails to generate learning | Log error, still move to Done (no learning appended) |
| Agent_Memory.md doesn't exist | Create it with starter template, then append |
| Agent_Memory.md too large (>50 learnings) | Log warning, still append. Human can prune manually. |

## Files Changed/Created

| File | Change |
|------|--------|
| `src/orchestrator.py` | Add `review_rejected()`, `get_rejected_actions()`, update `_invoke_claude()` to read Agent_Memory |
| `setup_vault.py` | Add `Rejected/` to vault folders, create `Agent_Memory.md` template |
| `main.py` | Add rejected-review step to main loop |
| `tests/test_orchestrator.py` | Tests for review_rejected, memory append, Claude prompt includes memory |
| `tests/test_integration.py` | E2e test: email → plan → reject → learning → memory updated |
| `tests/test_setup_vault.py` | Verify Rejected/ folder and Agent_Memory.md created |

## Out of Scope (Gold)

- Edit-diff detection in Approved/ (could be future enhancement)
- Reply quality scoring
- Periodic batch reviews
- Autonomous triage / auto-approve
- Cloud deployment (Platinum tier)
