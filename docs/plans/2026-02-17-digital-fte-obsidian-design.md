# Digital FTE — Obsidian Tier Design: Smart Email Prioritization

**Date:** 2026-02-17
**Tier:** Obsidian (after Diamond)
**Focus:** Rule-based email priority classification with processing order and vault tags

---

## Goal

Classify incoming emails as high / normal / low priority using deterministic rules (urgency keywords + VIP senders + newsletter patterns). Tag action files with priority in frontmatter so Obsidian can filter/sort. Process high-priority emails first.

## Architecture

```
Email arrives
    |
GmailWatcher.create_action_file()
    |
classify_priority(subject, body, sender)
    |
    +-- urgency keyword match? --> high
    +-- VIP sender match?      --> high
    +-- newsletter pattern?    --> low
    +-- else                   --> normal
    |
Needs_Action/email-*.md  (priority: high|normal|low in frontmatter)
    |
Orchestrator.get_pending_actions()  <-- sorted: high > normal > low
```

## Components

### 1. `src/priority.py` (NEW)

Single function: `classify_priority(subject: str, body: str, sender: str, vip_senders: list[str]) -> str`

Returns `"high"`, `"normal"`, or `"low"`.

**Classification rules:**
- **High**: subject or body contains any urgency keyword (case-insensitive: `urgent`, `asap`, `deadline`, `overdue`) OR sender email matches any entry in the VIP senders list
- **Low**: sender contains `noreply@`, `no-reply@`, `newsletter@`, `notifications@`, or `mailer-daemon@`
- **Normal**: everything else

**Edge cases:**
- Empty/missing fields default to `"normal"`
- Classification errors default to `"normal"`
- VIP check takes precedence over newsletter check (a VIP using noreply@ is still high)

### 2. `src/config.py` (MODIFY)

New config field:
- `vip_senders: list[str]` — parsed from `VIP_SENDERS` env var (comma-separated, default empty list)

### 3. `src/watchers/gmail_watcher.py` (MODIFY)

- Accept `vip_senders` parameter in constructor
- Call `classify_priority()` in `create_action_file()`
- Add `priority: high|normal|low` to action file frontmatter

### 4. `src/orchestrator.py` (MODIFY)

- `get_pending_actions()` reads frontmatter from each action file
- Sorts by priority: high first, then normal, then low

### 5. `main.py` (MODIFY)

- Pass `cfg.vip_senders` to GmailWatcher constructor

### 6. `.env.example` (MODIFY)

Add:
```
VIP_SENDERS=ceo@company.com,important-client@example.com
```

## Error Handling

- If `classify_priority()` raises any exception, caller catches and defaults to `"normal"`
- Missing or empty subject/body/sender are treated as empty strings

## Testing Strategy

- Unit tests for `classify_priority()`: keyword detection, VIP matching, newsletter detection, edge cases, precedence
- Unit tests for config: VIP_SENDERS parsing
- Unit tests for GmailWatcher: priority tag in frontmatter
- Unit tests for Orchestrator: sorted processing order
- E2E integration test: high-priority email processed before normal

## Non-Goals

- No Claude-based classification (too expensive per email)
- No priority-based auto-approve threshold changes
- No separate vault folders per priority level
- No file watcher priority (emails only)
