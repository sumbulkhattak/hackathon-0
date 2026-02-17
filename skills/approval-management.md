# Skill: Approval Management

## Description
Manage the human-in-the-loop approval pipeline. Route plans based on confidence scores, handle approvals and rejections, and execute approved actions.

## Approval Pipeline
```
Needs_Action/ → Orchestrator + Claude → confidence check
                                           │
                              ┌─────────────┴─────────────┐
                              │                           │
                    confidence >= threshold     confidence < threshold
                              │                           │
                         Approved/                Pending_Approval/
                              │                           │
                        Auto-execute              Human reviews
                              │                     │         │
                           Done/              Approved/   Rejected/
                                                  │         │
                                             Execute    Learn → Memory
                                                  │         │
                                               Done/     Done/
```

## Auto-Approve Rules
- Confidence must be >= `AUTO_APPROVE_THRESHOLD` (default 1.0 = disabled)
- Reply actions must pass daily send limit check
- If auto-send fails, falls back to `Pending_Approval/` for human review

## Human Approval
- Move file from `Pending_Approval/` to `Approved/` to approve
- Move file from `Pending_Approval/` to `Rejected/` to reject
- Web dashboard at localhost:8000 provides approve/reject buttons

## Configuration
- `AUTO_APPROVE_THRESHOLD=0.85` — confidence threshold (1.0 = disabled)
- `DAILY_SEND_LIMIT=20` — max emails per day

## Implementation
- Module: `src/orchestrator.py` → `process_action()`, `execute_approved()`, `review_rejected()`
- Web UI: `src/web.py` → `/approve/{filename}`, `/reject/{filename}`
