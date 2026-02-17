# Skill: Email Triage

## Description
Classify incoming emails by priority (high/normal/low) and route them to the appropriate vault folder for processing.

## Trigger
- Gmail Watcher detects a new unread email
- File is created in `vault/Needs_Action/`

## Classification Rules

### High Priority
- Subject or body contains urgency keywords: "urgent", "asap", "deadline", "overdue"
- Sender is in the VIP senders list (configured in `.env`)

### Low Priority
- Sender matches newsletter patterns: noreply@, no-reply@, newsletter@, notifications@, mailer-daemon@

### Normal Priority
- Everything else

## Input
```yaml
type: email
from: sender@example.com
subject: Email subject line
body: Email body text
```

## Output
A markdown file in `vault/Needs_Action/` with frontmatter:
```yaml
---
type: email
from: sender@example.com
subject: Email subject line
date: 2026-02-17T10:00:00Z
priority: high|normal|low
gmail_id: abc123
---
```

## Implementation
- Module: `src/priority.py` → `classify_priority()`
- Watcher: `src/watchers/gmail_watcher.py`
- Config: `VIP_SENDERS` in `.env`
