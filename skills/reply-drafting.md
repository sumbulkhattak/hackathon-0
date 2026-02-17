# Skill: Reply Drafting

## Description
Analyze an email action item, generate a professional reply draft, and include a confidence score for the plan.

## Trigger
- Orchestrator picks up a file from `vault/Needs_Action/`
- Claude is invoked to analyze the action item

## Process
1. Read the action file content
2. Read `vault/Company_Handbook.md` for tone and rules
3. Read `vault/Agent_Memory.md` for past learnings
4. Generate analysis, recommended actions, and reply draft
5. Include confidence score (0.0 to 1.0)

## Reply Format
The reply must be wrapped in markers:
```
---BEGIN REPLY---
Dear [Name],

Thank you for your email regarding [topic].

[Professional response based on Company Handbook rules]

Best regards,
[Signature]
---END REPLY---
```

## Confidence Scoring
- **0.9-1.0**: Routine reply to known contact, clear request
- **0.7-0.8**: Standard reply, some judgment needed
- **0.5-0.6**: Complex situation, multiple interpretations
- **Below 0.5**: Sensitive, ambiguous, or high-stakes

## Output
A plan file in `vault/Pending_Approval/` or auto-approved to `vault/Approved/` with:
```yaml
---
source: email-original.md
created: 2026-02-17T10:00:00Z
status: pending_approval
confidence: 0.85
action: reply
gmail_id: abc123
to: sender@example.com
subject: "Re: Original Subject"
---
```

## Implementation
- Module: `src/orchestrator.py` → `process_action()`, `_invoke_claude()`
- Utilities: `src/utils.py` → `extract_reply_block()`, `extract_confidence()`
