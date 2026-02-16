# Digital FTE — Silver Tier Design

**Date:** 2026-02-16
**Tier:** Silver
**Approach:** Extend Orchestrator (Approach A — minimal new code, no plugin system)

## Summary

Complete the email loop. Claude drafts reply text in plan files, humans approve in Obsidian, and the agent sends replies via Gmail API. No new watchers or MCP servers — focused scope.

## Scope

- **In scope:** Gmail reply sending for approved plans, daily send limit, updated Claude prompt, structured plan format
- **Out of scope:** New watchers, MCP servers, calendar/Slack, plugin/executor system

## Decisions

- **Execution model:** Extend `Orchestrator.execute_approved()` directly (no executor abstraction yet)
- **Send method:** Gmail API direct — reuse existing OAuth credentials, add `gmail.send` scope
- **Reply flow:** Claude drafts full reply → human reviews in `Pending_Approval/` → moves to `Approved/` → agent sends → archives to `Done/`
- **Safety:** Vault approval is the primary gate. Daily send limit (configurable, default 20) as a safety net.
- **Reply format:** Delimited `---BEGIN REPLY---` / `---END REPLY---` block in plan files

## Plan File Format

Plans that include a reply get structured frontmatter:

```markdown
---
source: email-invoice-1234.md
created: 2026-02-16T10:30:00Z
status: pending_approval
action: reply
gmail_id: 18d7a3b2c1e4f567
to: sender@example.com
subject: "Re: Invoice #1234"
---

# Plan: email-invoice-1234

## Analysis
[Claude's analysis of the email]

## Recommended Actions
1. Reply acknowledging receipt of invoice

## Reply Draft
---BEGIN REPLY---
Hi [Name],

Thank you for sending Invoice #1234. I've received it and will process payment by [date].

Best regards
---END REPLY---
```

- `action: reply` signals the orchestrator to send
- Plans without `action` field behave as Bronze (analysis only, move to Done)
- Human can edit the reply text in Obsidian before approving

## Gmail Send Integration

### OAuth Scope

Add `https://www.googleapis.com/auth/gmail.send` to existing auth scopes in `src/auth.py`. Users will need to re-authenticate to grant the new scope.

### New Module: `src/gmail_sender.py`

```python
def send_reply(gmail_service, gmail_id: str, to: str, subject: str, body: str) -> dict:
    """Send a reply to an existing email thread."""
    # 1. Fetch original message to get threadId and Message-ID header
    # 2. Build MIME message with In-Reply-To and References headers
    # 3. Call gmail.users().messages().send() with threadId
    # 4. Return sent message metadata
```

Replies use the original email's `threadId` and set `In-Reply-To` / `References` headers for proper Gmail threading.

### Daily Send Limit

- Tracked in `vault/Logs/.send_count_YYYY-MM-DD.json`
- Before each send: check if limit reached
- Configurable via `DAILY_SEND_LIMIT` env var (default: 20)
- When limit reached: log warning, skip file, leave in `Approved/` for next day

## Orchestrator Changes

### `execute_approved()` — extended

```python
def execute_approved(self, approved_file: Path) -> Path:
    metadata = parse_frontmatter(approved_file)

    if metadata.get("action") == "reply":
        reply_body = extract_reply_block(approved_file)
        send_reply(
            gmail_service=self.gmail_service,
            gmail_id=metadata["gmail_id"],
            to=metadata["to"],
            subject=metadata["subject"],
            body=reply_body,
        )
        log_action(..., action="email_sent", ...)

    # Move to Done/ (same as before)
    shutil.move(approved_file, self.done / approved_file.name)
```

### `__init__` — new parameters

- `gmail_service` — Gmail API service object (passed from `main.py`)
- `daily_send_limit` — integer (from config)

### `_invoke_claude` — updated prompt

Instruct Claude to include `action: reply`, `to`, `subject`, and the `---BEGIN REPLY---` block when a reply is appropriate. Claude can still produce plans without `action` for analysis-only items.

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Gmail send failure | Log error, leave in `Approved/` for retry next cycle |
| Daily limit reached | Log warning, skip file, leave in `Approved/` |
| Missing frontmatter fields | Log error, move to `Done/` with `status: failed` |
| Missing reply block | Log error, move to `Done/` with `status: failed` |

## Configuration

New `.env` variable:

| Variable | Default | Description |
|----------|---------|-------------|
| `DAILY_SEND_LIMIT` | `20` | Max emails sent per day |

## Files Changed/Created

| File | Change |
|------|--------|
| `src/auth.py` | Add `gmail.send` scope |
| `src/gmail_sender.py` | **New** — `send_reply()` + `check_send_limit()` |
| `src/orchestrator.py` | Extend `execute_approved()`, update Claude prompt, accept `gmail_service` |
| `src/config.py` | Add `daily_send_limit` field |
| `src/utils.py` | Add `parse_frontmatter()` and `extract_reply_block()` helpers |
| `main.py` | Pass `gmail_service` to orchestrator |
| `.env.example` | Add `DAILY_SEND_LIMIT=20` |
| `tests/test_gmail_sender.py` | **New** — sender unit tests |
| `tests/test_orchestrator.py` | Extend with reply execution tests |
| `tests/test_integration.py` | Extend with full reply flow |

## Testing

- `test_gmail_sender.py` — message building, threading headers, error cases (mocked Gmail API)
- `test_orchestrator.py` — reply execution path, frontmatter parsing, send limit enforcement
- `test_integration.py` — full flow: email in → Claude plan with reply → approve → send (mocked) → done
- Send limit: counter increments, blocks at limit, resets on new day

## Out of Scope (Silver)

- Multiple watchers (Gold tier)
- Ralph Wiggum loops (Gold tier)
- Action executor plugin system (refactor when needed)
- Cloud deployment (Platinum tier)
- WhatsApp/LinkedIn/Slack integration
