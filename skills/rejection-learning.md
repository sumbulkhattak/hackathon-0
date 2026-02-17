# Skill: Rejection Learning

## Description
When a human rejects a plan, analyze what went wrong and store the learning in Agent Memory to improve future decisions.

## Trigger
- A file appears in `vault/Rejected/`

## Process
1. Read the rejected plan content
2. Read current `vault/Agent_Memory.md`
3. Invoke Claude to analyze the rejection reason
4. Extract a concise learning (1-2 sentences)
5. Append the learning to `vault/Agent_Memory.md` with timestamp
6. Move the rejected file to `vault/Done/`

## Learning Format
```markdown
- **2026-02-17T10:30:00Z** — Rejected plan for "plan-invoice-reply": The tone was too casual for a formal invoice dispute. Use formal language for financial matters.
```

## Memory Integration
- Agent Memory is read by Claude alongside Company Handbook on every plan generation
- Learnings accumulate over time, improving plan quality
- Patterns emerge: e.g., "always use formal tone for financial topics"

## Implementation
- Module: `src/orchestrator.py` → `review_rejected()`, `_invoke_claude_review()`
- Memory: `vault/Agent_Memory.md`
