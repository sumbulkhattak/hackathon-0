# Skill: Email Sending

## Description
Send threaded Gmail replies for approved plans, with rate limiting and audit logging.

## Trigger
- A file appears in `vault/Approved/` with `action: reply` in frontmatter

## Prerequisites
- Gmail API OAuth 2.0 credentials in `credentials/client_secret.json`
- Approved plan must contain `---BEGIN REPLY---` / `---END REPLY---` markers
- Daily send count must be under `DAILY_SEND_LIMIT`

## Process
1. Read approved file frontmatter: `gmail_id`, `to`, `subject`
2. Extract reply body from between markers
3. Check daily send limit
4. Construct MIME message with proper threading headers:
   - `In-Reply-To`: original message ID
   - `References`: original message ID
   - `threadId`: original Gmail thread ID
5. Send via Gmail API
6. Increment daily send counter
7. Log action to `vault/Logs/`
8. Move file to `vault/Done/`

## Rate Limiting
- Daily counter stored in `vault/Logs/.send_count_YYYY-MM-DD.json`
- Default limit: 20 emails/day (configurable via `DAILY_SEND_LIMIT`)
- When limit reached: skip sending, leave file in Approved/

## Error Handling
- Send failure: leave file in Approved/ for retry
- Missing reply block: move to Done/ as failed
- Auto-approve send failure: fall back to Pending_Approval/

## Implementation
- Module: `src/gmail_sender.py` → `send_reply()`, `check_send_limit()`, `increment_send_count()`
- Orchestrator: `src/orchestrator.py` → `execute_approved()`
