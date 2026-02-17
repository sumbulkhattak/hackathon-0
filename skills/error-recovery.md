# Skill: Error Recovery and Graceful Degradation

## Description
Handles transient failures with exponential backoff retry, quarantines irrecoverable actions for later retry, and ensures watchers continue collecting when Claude or APIs are unavailable.

## Trigger
- Any API call or external service interaction that fails with a transient error (network timeout, rate limit, 5xx)
- Claude CLI unavailable or timed out during plan generation
- Gmail API returning temporary errors

## Safety Rules
- **Never auto-retry payments.** Payment-related actions always require human approval, even after recovery.
- **Watchers continue collecting when Claude is unavailable.** File watcher and Gmail watcher deposit items into `vault/Needs_Action/` independently of Claude availability.
- **PermanentError stops immediately.** Authentication revocation, bad data, or invalid credentials are not retried.

## Retry Strategy
1. On TransientError, retry up to `max_attempts` (default: 3)
2. Exponential backoff: `base_delay * 2^attempt` seconds between retries
3. Delay capped at `max_delay` (default: 60 seconds)
4. Optional `on_failure` callback for logging/alerting on each failure

## Quarantine Queue
When all retries are exhausted:
1. Move the failed action file to `vault/Quarantine/`
2. Add `quarantine_error` and `quarantine_time` to frontmatter
3. `process_quarantine()` periodically checks items older than 5 minutes
4. Eligible items are restored to `vault/Needs_Action/` with quarantine metadata stripped

## Error Classification
| Error Type | Examples | Retry? |
|-----------|---------|--------|
| TransientError | Network timeout, API rate limit, 503 | Yes (exponential backoff) |
| PermanentError | Auth revoked, invalid data, 401/403 | No (fail immediately) |

## Implementation
- Module: `src/retry.py`
  - `TransientError` — exception class for retryable errors
  - `PermanentError` — exception class for non-retryable errors
  - `with_retry()` — decorator with exponential backoff
  - `queue_failed_action()` — move failed action to Quarantine/
  - `process_quarantine()` — restore old quarantined items to Needs_Action/
- Vault folder: `vault/Quarantine/`
- Tests: `tests/test_retry.py` (13 tests)
