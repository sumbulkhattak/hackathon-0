# Digital FTE — Architecture Documentation

## System Overview

The Digital FTE is an autonomous AI agent that manages personal and business affairs through an Obsidian vault. It follows a **Perception → Reasoning → Action → Memory** architecture, powered by Claude Code as the reasoning engine.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SOURCES                              │
├──────────────┬──────────────┬──────────────┬────────────────────┤
│    Gmail     │   Files      │ Social Media │   Scheduling       │
│  (OAuth 2.0) │ (PDF/Images) │ (LinkedIn,   │  (cron/Task Sched) │
│              │              │  FB, Twitter) │                    │
└──────┬───────┴──────┬───────┴──────┬───────┴────────┬───────────┘
       │              │              │                │
       ▼              ▼              ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PERCEPTION LAYER (Watchers)                   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │
│  │ Gmail Watcher│ │ File Watcher │ │ Scheduler (cron/one-shot)│ │
│  │ + Priority   │ │ + PDF/Vision │ │                          │ │
│  │ Classifier   │ │ Extraction   │ │                          │ │
│  └──────┬───────┘ └──────┬───────┘ └────────────┬─────────────┘ │
└─────────┼────────────────┼──────────────────────┼───────────────┘
          │                │                      │
          ▼                ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OBSIDIAN VAULT (Local Memory)                 │
│                                                                  │
│  ┌────────────┐ ┌─────────────────┐ ┌──────────┐ ┌───────────┐ │
│  │Needs_Action│ │Pending_Approval │ │ Approved │ │  Done     │ │
│  ├────────────┤ ├─────────────────┤ ├──────────┤ ├───────────┤ │
│  │ Inbox      │ │ Rejected        │ │Quarantine│ │ Briefings │ │
│  ├────────────┤ ├─────────────────┤ ├──────────┤ ├───────────┤ │
│  │ Logs       │ │ Dashboard.md    │ │Memory.md │ │Handbook.md│ │
│  └────────────┘ └─────────────────┘ └──────────┘ └───────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    REASONING LAYER (Claude Code)                 │
│                                                                  │
│  Orchestrator.py ──► Claude CLI ──► Plan Generation              │
│       │                                    │                     │
│       │            ┌───────────────────────┤                     │
│       │            │                       │                     │
│  confidence ≥ threshold?        confidence < threshold?          │
│       │            │                       │                     │
│  Auto-execute  Pending_Approval      Human Review                │
│       │                                    │                     │
│  Ralph Wiggum Loop                  Approve / Reject             │
│  (autonomous iteration)                    │                     │
│                                     Learning → Memory            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ACTION LAYER (MCP Servers + Direct)           │
│                                                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │
│  │ Email MCP    │ │ Social MCP   │ │ Direct Actions           │ │
│  │ - send_email │ │ - LinkedIn   │ │ - Gmail API replies      │ │
│  │ - search     │ │ - Facebook   │ │ - File operations        │ │
│  │ - list_pend  │ │ - Twitter    │ │ - Dashboard update       │ │
│  │ - vault_stat │ │ - draft_post │ │ - CEO Briefing           │ │
│  └──────────────┘ └──────────────┘ └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    INTERFACE LAYER                               │
│                                                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │
│  │ Web Dashboard│ │ Obsidian     │ │ REST API                 │ │
│  │ (FastAPI)    │ │ Dashboard.md │ │ /api/status              │ │
│  │ Approve/     │ │              │ │ /api/pending             │ │
│  │ Reject UI    │ │              │ │ /api/activity            │ │
│  └──────────────┘ └──────────────┘ └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### 1. File-System as Message Queue
Instead of a database or message broker, the vault folders act as queues:
- `Needs_Action/` = inbox queue
- `Pending_Approval/` = approval queue
- `Approved/` = execution queue
- `Done/` = archive

**Why:** Local-first, human-readable, works with Obsidian, no external dependencies.

### 2. Claude CLI over API
We invoke Claude via `claude --print` subprocess rather than the Anthropic API.

**Why:** The hackathon requires Claude Code as the reasoning engine. CLI invocation is simpler and doesn't require API keys.

### 3. Confidence-Based Auto-Approve
Plans include a 0.0-1.0 confidence score. Above threshold = auto-execute.

**Why:** Balances autonomy with safety. Low-confidence plans get human review. Default threshold 1.0 means everything gets reviewed until the user opts in.

### 4. Priority Classification
Rule-based (not ML) classification using keywords, VIP lists, and newsletter patterns.

**Why:** Deterministic, testable, no training data needed. Easy to customize via Company_Handbook.md and .env.

### 5. Ralph Wiggum Loop
Keeps Claude iterating until task completion using promise-based or file-movement detection.

**Why:** Prevents Claude from stopping prematurely on multi-step tasks. Safety limited by max_iterations.

## Error Handling Strategy

| Error Type | Strategy | Example |
|------------|----------|---------|
| Transient | Exponential backoff retry (max 3) | Network timeout, API rate limit |
| Permanent | Fail immediately, quarantine | Auth revoked, corrupt data |
| Logic | Route to human review queue | Claude misinterprets message |
| System | Log and continue | Disk full, process crash |

## Security Model

1. **Credential isolation:** OAuth tokens in `credentials/` (gitignored), API keys in `.env` (gitignored)
2. **Human-in-the-loop:** All sensitive actions require approval unless confidence threshold met
3. **Rate limiting:** Daily email send limit prevents runaway sends
4. **Audit logging:** Every action logged to `vault/Logs/` in JSON format
5. **Quarantine:** Failed actions isolated for review rather than silently retried

## Testing Strategy

- **215+ unit tests** covering all modules
- **Integration tests** for end-to-end pipeline flows
- **Mock-based testing** for external APIs (Gmail, Claude, social media)
- **TDD throughout:** Every feature started with failing tests

## Lessons Learned

1. **File-based communication is surprisingly effective** — Folders as queues work well for human-in-the-loop workflows. Obsidian makes the state visible and editable.

2. **Confidence scoring needs calibration** — Auto-approve threshold should start at 1.0 (disabled) and be lowered gradually as trust builds.

3. **Priority classification needs domain knowledge** — Generic urgency keywords work, but VIP senders and custom rules in Company_Handbook.md are more valuable.

4. **Error quarantine > silent retry** — Moving failed items to a quarantine folder (with metadata) is safer than automatic retry, especially for payment and email actions.

5. **Dashboard as the single pane of glass** — Both Dashboard.md (for Obsidian) and the web dashboard (for browser) serve as entry points for monitoring system state.

## Module Map

| Module | Purpose | Lines |
|--------|---------|-------|
| `src/orchestrator.py` | Central pipeline orchestration | ~350 |
| `src/watchers/gmail_watcher.py` | Gmail polling and action file creation | ~130 |
| `src/watchers/file_watcher.py` | PDF/image file detection and extraction | ~140 |
| `src/priority.py` | Email priority classification | ~45 |
| `src/extractors.py` | PDF text + image vision extraction | ~70 |
| `src/gmail_sender.py` | Email sending with rate limiting | ~70 |
| `src/dashboard.py` | Dashboard.md generation | ~135 |
| `src/web.py` | FastAPI web dashboard | ~450 |
| `src/ralph_wiggum.py` | Autonomous task completion loop | ~220 |
| `src/retry.py` | Error recovery with retry + quarantine | ~185 |
| `src/briefing.py` | CEO Briefing generation | ~250 |
| `src/social.py` | Social media posting | ~170 |
| `src/scheduler.py` | Cron/Task Scheduler integration | ~175 |
| `mcp_servers/email_server.py` | Email MCP server (4 tools) | ~190 |
| `mcp_servers/social_server.py` | Social Media MCP server (5 tools) | ~130 |
