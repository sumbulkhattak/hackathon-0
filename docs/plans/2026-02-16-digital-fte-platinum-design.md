# Digital FTE — Platinum Tier Design

**Date:** 2026-02-16
**Tier:** Platinum
**Approach:** Extend Orchestrator (Approach A — inline auto-approve in process_action)

## Summary

Add confidence-based auto-approve so the agent can execute low-risk plans without human review. Claude self-scores each plan (0.0-1.0). Plans scoring above a configurable threshold skip Pending_Approval/ and execute immediately. Disabled by default (threshold=1.0).

## Scope

- **In scope:** Claude confidence scoring, auto-approve routing in process_action(), config threshold, audit logging, fallback on failure
- **Out of scope:** Historical track record scoring, category allowlists, cooldown periods, multi-step workflows, dashboard

## Decisions

- **Scoring method:** Claude self-scores (0.0-1.0) in a `## Confidence` section of its response
- **Control mechanism:** Single env var `AUTO_APPROVE_THRESHOLD` (default: 1.0 = disabled)
- **Auto-approve flow:** Execute immediately, log as `auto_approved` with confidence score
- **Architecture:** Extend process_action() inline (no new classes or folders)
- **Safety fallback:** Missing/invalid confidence defaults to 0.0 (always requires human review)

## Confidence Score

Claude's response format is updated to include:

```
## Confidence
[0.0 to 1.0 — how confident you are this plan needs no human edits]
```

Parsed by a new `extract_confidence()` utility. Written into plan frontmatter as `confidence: 0.85`.

## Auto-Approve Flow

```
Needs_Action/
      │
  process_action()
      │
  Claude generates plan + confidence score
      │
  confidence >= threshold?
     │          │
    YES         NO
     │          │
  Approved/   Pending_Approval/
     │          │
  execute_approved()   Human reviews
     │          │
  Done/     Approved/ or Rejected/
  (logged as auto_approved)
```

### Routing logic in process_action():

1. Parse confidence from Claude's response
2. Add `confidence: X.XX` to plan frontmatter
3. If confidence >= threshold AND daily send limit not hit:
   - Write plan to Approved/
   - Call execute_approved() immediately
   - Log as `auto_approved`
4. If confidence < threshold OR send limit hit:
   - Route to Pending_Approval/ as today

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTO_APPROVE_THRESHOLD` | `1.0` | Confidence threshold. Default 1.0 = disabled (nothing auto-approves). Set to e.g. 0.85 to enable. |

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Claude doesn't include `## Confidence` | Default to 0.0 — requires human approval |
| Confidence value not a valid float | Default to 0.0 — requires human approval |
| Auto-approved reply fails to send | Log error, move plan to Pending_Approval/ for human review |
| Daily send limit reached during auto-approve | Route to Pending_Approval/ instead of executing |

## Logging

Auto-approved actions get a distinct log entry:
- `action: "auto_approved"`
- `result: "confidence:0.92,reply_to:bob@test.com"` (or similar)

This creates a clear audit trail for reviewing agent autonomy.

## Files Changed/Created

| File | Change |
|------|--------|
| `src/config.py` | Add `auto_approve_threshold: float` field |
| `src/utils.py` | Add `extract_confidence()` function |
| `src/orchestrator.py` | Update `_invoke_claude()` prompt, update `process_action()` with auto-approve routing |
| `main.py` | Pass `auto_approve_threshold` to Orchestrator |
| `README.md` | Update for Platinum tier |
| `tests/test_utils.py` | Tests for `extract_confidence()` |
| `tests/test_orchestrator.py` | Tests for auto-approve routing |
| `tests/test_integration.py` | E2e auto-approve test |

## Out of Scope (Platinum)

- Historical track record scoring (could combine with self-score later)
- Category-based allowlists (e.g. "never auto-approve financial")
- Cooldown / learning period before auto-approve activates
- Multi-step workflow chaining
- Dashboard / analytics
- Cloud deployment
