# Digital FTE — Bronze Tier Design

**Date:** 2026-02-16
**Tier:** Bronze (8-12 hours)
**Approach:** Monolith (single Python project)

## Summary

Build an autonomous AI agent ("Digital FTE") that monitors Gmail, creates actionable markdown files in an Obsidian vault, and uses Claude Code to analyze and plan responses — with human-in-the-loop approval for sensitive actions.

## Decisions

- **Tier:** Bronze — one watcher, basic Claude integration, Obsidian vault
- **Watcher:** Gmail (Google API + OAuth 2.0)
- **Architecture:** Monolith — single Python project, folder-based communication
- **Obsidian:** New vault created from scratch
- **Execution model:** Watcher polls Gmail → drops action files → orchestrator invokes Claude → plans created → human approves → action logged

## Project Structure

```
hackathon-0/
├── vault/                          # Obsidian vault
│   ├── Needs_Action/               # Watcher drops action files here
│   ├── Plans/                      # Claude creates plan files here
│   ├── Pending_Approval/           # Items needing human sign-off
│   ├── Approved/                   # Human-approved actions
│   ├── Done/                       # Completed items
│   ├── Logs/                       # Daily JSON logs
│   └── Company_Handbook.md         # Rules & preferences for Claude
├── src/
│   ├── watchers/
│   │   ├── __init__.py
│   │   ├── base_watcher.py         # Abstract base class
│   │   └── gmail_watcher.py        # Gmail API polling
│   ├── orchestrator.py             # Reads Needs_Action, invokes Claude
│   ├── config.py                   # Env vars, paths, settings
│   └── utils.py                    # Logging, file helpers
├── credentials/                    # .gitignored — OAuth tokens
├── .env                            # .gitignored — secrets
├── .env.example                    # Template with placeholder values
├── requirements.txt
├── setup_vault.py                  # One-time vault initialization
└── main.py                         # Entry point
```

## Gmail Watcher

- Authenticates via Google OAuth 2.0
- Polls every 60 seconds (configurable) for unread emails
- Creates markdown action files in `vault/Needs_Action/` with YAML frontmatter
- Applies "Processed-by-FTE" Gmail label to prevent duplicate processing
- Configurable filter (default: `is:unread`)

### Action File Format

```markdown
---
type: email
from: sender@example.com
subject: Invoice #1234
date: 2026-02-16T10:30:00Z
priority: normal
gmail_id: 18d7a3b2c1e4f567
---

# New Email: Invoice #1234

**From:** sender@example.com
**Date:** 2026-02-16 10:30 AM

## Body
[Email body content]

## Suggested Actions
- [ ] Reply
- [ ] Forward
- [ ] Archive
```

## Orchestrator

- Uses `watchdog` library to detect new files in `vault/Needs_Action/`
- Reads action file + `Company_Handbook.md` for context
- Invokes Claude Code via subprocess with structured prompt
- Claude generates plan files in `vault/Plans/`
- Plans requiring approval move to `vault/Pending_Approval/`
- Watches `vault/Approved/` — when human approves, logs the execution
- Completed items move to `vault/Done/`

### Pipeline Flow

```
Needs_Action → [Claude processes] → Plans → Pending_Approval → [Human approves] → Approved → [Log] → Done
```

## Security & Configuration

### Credentials
- Gmail OAuth tokens in `credentials/` (.gitignored)
- All secrets in `.env` (.gitignored)
- `.env.example` committed with placeholders

### .env Variables
```
VAULT_PATH=./vault
GMAIL_CHECK_INTERVAL=60
GMAIL_FILTER=is:unread
CLAUDE_MODEL=claude-sonnet-4-5-20250929
LOG_LEVEL=INFO
```

### Error Handling
- Gmail API failures: exponential backoff (3 retries)
- File I/O errors: log and skip
- Claude subprocess failures: log, leave in Needs_Action for retry
- No crash-on-error: loop continues on individual failures

### Logging
- `vault/Logs/YYYY-MM-DD.json` — structured action logs
- Each entry: `{timestamp, actor, action, source, result}`
- Python `logging` for console output

## Dependencies

- `google-api-python-client` — Gmail API
- `google-auth-oauthlib` — OAuth 2.0 flow
- `watchdog` — filesystem monitoring
- `python-dotenv` — env var loading
- `pyyaml` — YAML frontmatter parsing

## Out of Scope (Bronze)

- MCP servers for email sending (Silver tier)
- Multiple watchers (Silver tier)
- Ralph Wiggum loops (Gold tier)
- Cloud deployment (Platinum tier)
- WhatsApp/LinkedIn integration
- Payment processing
