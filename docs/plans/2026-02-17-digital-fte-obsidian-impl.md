# Smart Email Prioritization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Classify incoming emails as high/normal/low priority using rule-based keywords and VIP senders, tag action files, and process high-priority emails first.

**Architecture:** New `src/priority.py` module with `classify_priority()` function. GmailWatcher calls it when creating action files, embedding priority in frontmatter. Orchestrator sorts pending actions by priority (high first).

**Tech Stack:** Python 3.13, pytest, no new dependencies

---

### Task 1: Create `classify_priority()` — urgency keyword detection

**Files:**
- Create: `src/priority.py`
- Create: `tests/test_priority.py`

**Step 1: Write failing tests**

```python
"""Tests for email priority classification."""
import pytest

from src.priority import classify_priority


URGENCY_KEYWORDS = ["urgent", "asap", "deadline", "overdue"]


def test_classify_high_on_urgency_keyword_in_subject():
    """Emails with urgency keywords in subject should be high priority."""
    result = classify_priority(subject="URGENT: Please review", body="", sender="someone@example.com")
    assert result == "high"


def test_classify_high_on_urgency_keyword_in_body():
    """Emails with urgency keywords in body should be high priority."""
    result = classify_priority(subject="Review needed", body="This is asap, please handle.", sender="someone@example.com")
    assert result == "high"


def test_classify_high_is_case_insensitive():
    """Urgency keyword detection should be case-insensitive."""
    result = classify_priority(subject="DeAdLiNe approaching", body="", sender="someone@example.com")
    assert result == "high"


def test_classify_normal_without_keywords():
    """Emails without urgency keywords should be normal priority."""
    result = classify_priority(subject="Weekly update", body="Here is the weekly report.", sender="someone@example.com")
    assert result == "normal"
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_priority.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.priority'`

**Step 3: Write minimal implementation**

```python
"""Email priority classification based on rules."""
import logging

logger = logging.getLogger("digital_fte.priority")

URGENCY_KEYWORDS = ["urgent", "asap", "deadline", "overdue"]


def classify_priority(
    subject: str = "",
    body: str = "",
    sender: str = "",
    vip_senders: list[str] | None = None,
) -> str:
    """Classify email priority as 'high', 'normal', or 'low'.

    Rules (evaluated in order):
    - High: urgency keyword in subject/body OR sender in VIP list
    - Low: sender matches newsletter/notification patterns
    - Normal: everything else
    """
    subject_lower = subject.lower()
    body_lower = body.lower()

    # Check urgency keywords
    for keyword in URGENCY_KEYWORDS:
        if keyword in subject_lower or keyword in body_lower:
            return "high"

    return "normal"
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_priority.py -v`
Expected: 4 PASSED

**Step 5: Commit**

```bash
git add src/priority.py tests/test_priority.py
git commit -m "feat: add classify_priority with urgency keyword detection"
```

---

### Task 2: Add VIP sender detection to `classify_priority()`

**Files:**
- Modify: `tests/test_priority.py`
- Modify: `src/priority.py`

**Step 1: Write failing tests**

Append to `tests/test_priority.py`:

```python
def test_classify_high_on_vip_sender():
    """Emails from VIP senders should be high priority."""
    result = classify_priority(
        subject="Hello", body="Regular message.",
        sender="ceo@company.com", vip_senders=["ceo@company.com"],
    )
    assert result == "high"


def test_classify_vip_sender_case_insensitive():
    """VIP sender matching should be case-insensitive."""
    result = classify_priority(
        subject="Hello", body="",
        sender="CEO@Company.com", vip_senders=["ceo@company.com"],
    )
    assert result == "high"


def test_classify_normal_when_vip_list_empty():
    """Non-VIP sender with empty VIP list should be normal."""
    result = classify_priority(
        subject="Hello", body="Regular message.",
        sender="someone@example.com", vip_senders=[],
    )
    assert result == "normal"


def test_classify_normal_when_vip_list_none():
    """When vip_senders is None, VIP check should be skipped."""
    result = classify_priority(
        subject="Hello", body="",
        sender="ceo@company.com", vip_senders=None,
    )
    assert result == "normal"
```

**Step 2: Run tests to verify new tests fail**

Run: `python -m pytest tests/test_priority.py -v`
Expected: `test_classify_high_on_vip_sender` FAILS (returns "normal")

**Step 3: Add VIP sender logic to `classify_priority()`**

In `src/priority.py`, after the urgency keyword loop, add:

```python
    # Check VIP senders
    if vip_senders:
        sender_lower = sender.lower()
        for vip in vip_senders:
            if vip.lower() == sender_lower:
                return "high"
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_priority.py -v`
Expected: 8 PASSED

**Step 5: Commit**

```bash
git add src/priority.py tests/test_priority.py
git commit -m "feat: add VIP sender detection to classify_priority"
```

---

### Task 3: Add newsletter/low-priority detection to `classify_priority()`

**Files:**
- Modify: `tests/test_priority.py`
- Modify: `src/priority.py`

**Step 1: Write failing tests**

Append to `tests/test_priority.py`:

```python
NEWSLETTER_PATTERNS = ["noreply@", "no-reply@", "newsletter@", "notifications@", "mailer-daemon@"]


def test_classify_low_on_noreply_sender():
    """Emails from noreply addresses should be low priority."""
    result = classify_priority(subject="Your receipt", body="", sender="noreply@store.com")
    assert result == "low"


def test_classify_low_on_newsletter_sender():
    """Emails from newsletter addresses should be low priority."""
    result = classify_priority(subject="Weekly digest", body="", sender="newsletter@blog.com")
    assert result == "low"


def test_classify_low_on_notifications_sender():
    """Emails from notifications addresses should be low priority."""
    result = classify_priority(subject="New activity", body="", sender="notifications@github.com")
    assert result == "low"


def test_classify_low_is_case_insensitive():
    """Newsletter pattern detection should be case-insensitive."""
    result = classify_priority(subject="Receipt", body="", sender="NoReply@Store.com")
    assert result == "low"


def test_vip_takes_precedence_over_newsletter():
    """VIP sender should be high even if sender matches newsletter pattern."""
    result = classify_priority(
        subject="Important", body="",
        sender="noreply@vip-company.com",
        vip_senders=["noreply@vip-company.com"],
    )
    assert result == "high"
```

**Step 2: Run tests to verify new tests fail**

Run: `python -m pytest tests/test_priority.py -v`
Expected: `test_classify_low_on_noreply_sender` FAILS (returns "normal")

**Step 3: Add newsletter detection**

In `src/priority.py`, add the constant and logic:

```python
NEWSLETTER_PATTERNS = ["noreply@", "no-reply@", "newsletter@", "notifications@", "mailer-daemon@"]
```

After the VIP sender check, before `return "normal"`:

```python
    # Check newsletter/notification patterns
    sender_lower = sender.lower()
    for pattern in NEWSLETTER_PATTERNS:
        if pattern in sender_lower:
            return "low"
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_priority.py -v`
Expected: 13 PASSED

**Step 5: Commit**

```bash
git add src/priority.py tests/test_priority.py
git commit -m "feat: add newsletter/low-priority detection to classify_priority"
```

---

### Task 4: Add edge case handling to `classify_priority()`

**Files:**
- Modify: `tests/test_priority.py`
- Modify: `src/priority.py` (if needed)

**Step 1: Write failing tests**

Append to `tests/test_priority.py`:

```python
def test_classify_handles_empty_strings():
    """Empty subject, body, and sender should return normal."""
    result = classify_priority(subject="", body="", sender="")
    assert result == "normal"


def test_classify_handles_keyword_as_substring():
    """Urgency keyword as substring should still match (e.g., 'overdue' in 'overdue-invoice')."""
    result = classify_priority(subject="overdue-invoice reminder", body="", sender="billing@co.com")
    assert result == "high"


def test_classify_defaults_to_normal_on_exception():
    """If classification fails for any reason, default to normal."""
    # Pass types that would cause issues if not handled
    result = classify_priority(subject="Hello", body="World", sender="test@test.com")
    assert result in ("high", "normal", "low")
```

**Step 2: Run tests to verify they pass or fail**

Run: `python -m pytest tests/test_priority.py -v`
Expected: These should all PASS with current implementation (edge cases already handled). If any fail, fix.

**Step 3: Commit**

```bash
git add tests/test_priority.py
git commit -m "test: add edge case tests for classify_priority"
```

---

### Task 5: Add `vip_senders` config field

**Files:**
- Modify: `src/config.py:8-18` (Config dataclass)
- Modify: `src/config.py:21-34` (load_config function)
- Modify: `tests/test_config.py`

**Step 1: Write failing tests**

Append to `tests/test_config.py`:

```python
def test_config_loads_vip_senders(monkeypatch):
    """Config should parse VIP_SENDERS as a list of emails."""
    monkeypatch.setenv("VIP_SENDERS", "ceo@co.com,client@big.com")
    from src.config import load_config
    cfg = load_config()
    assert cfg.vip_senders == ["ceo@co.com", "client@big.com"]


def test_config_vip_senders_default_empty(monkeypatch):
    """Config should default vip_senders to empty list."""
    monkeypatch.delenv("VIP_SENDERS", raising=False)
    from src.config import load_config
    cfg = load_config()
    assert cfg.vip_senders == []


def test_config_vip_senders_strips_whitespace(monkeypatch):
    """Config should strip whitespace from VIP sender entries."""
    monkeypatch.setenv("VIP_SENDERS", " ceo@co.com , client@big.com ")
    from src.config import load_config
    cfg = load_config()
    assert cfg.vip_senders == ["ceo@co.com", "client@big.com"]
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL — `Config.__init__() got an unexpected keyword argument 'vip_senders'` or `AttributeError`

**Step 3: Add `vip_senders` to Config**

In `src/config.py`, add field to dataclass (after line 18):

```python
    vip_senders: list[str]
```

In `load_config()`, add parsing (after line 33):

```python
        vip_senders=[s.strip() for s in os.getenv("VIP_SENDERS", "").split(",") if s.strip()],
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_config.py -v`
Expected: 10 PASSED

**Step 5: Run full suite to check for regressions**

Run: `python -m pytest tests/ -v`
Expected: All pass (Config change is backward-compatible since it has a default)

**Step 6: Commit**

```bash
git add src/config.py tests/test_config.py
git commit -m "feat: add vip_senders config (VIP_SENDERS env var)"
```

---

### Task 6: Wire `classify_priority()` into GmailWatcher

**Files:**
- Modify: `src/watchers/gmail_watcher.py:7` (add import)
- Modify: `src/watchers/gmail_watcher.py:15` (constructor — add vip_senders param)
- Modify: `src/watchers/gmail_watcher.py:39-65` (create_action_file — call classify_priority)
- Modify: `tests/watchers/test_gmail_watcher.py`

**Step 1: Write failing tests**

Append to `tests/watchers/test_gmail_watcher.py`:

```python
def test_gmail_watcher_accepts_vip_senders(vault, mock_gmail_service):
    """GmailWatcher should accept and store vip_senders parameter."""
    from src.watchers.gmail_watcher import GmailWatcher
    watcher = GmailWatcher(
        vault_path=vault, gmail_service=mock_gmail_service,
        vip_senders=["boss@co.com"],
    )
    assert watcher.vip_senders == ["boss@co.com"]


def test_gmail_watcher_vip_senders_default_empty(vault, mock_gmail_service):
    """GmailWatcher should default vip_senders to empty list."""
    from src.watchers.gmail_watcher import GmailWatcher
    watcher = GmailWatcher(vault_path=vault, gmail_service=mock_gmail_service)
    assert watcher.vip_senders == []


def test_action_file_has_high_priority_for_urgent_email(vault, mock_gmail_service):
    """Action file should have priority: high when subject contains urgency keyword."""
    from src.watchers.gmail_watcher import GmailWatcher
    watcher = GmailWatcher(vault_path=vault, gmail_service=mock_gmail_service)
    item = {
        "id": "msg_urg",
        "from": "someone@example.com",
        "subject": "URGENT: Server is down",
        "date": "2026-02-17",
        "body": "The production server is down.",
        "labels": ["INBOX"],
    }
    path = watcher.create_action_file(item)
    content = path.read_text()
    assert "priority: high" in content


def test_action_file_has_low_priority_for_newsletter(vault, mock_gmail_service):
    """Action file should have priority: low for newsletter senders."""
    from src.watchers.gmail_watcher import GmailWatcher
    watcher = GmailWatcher(vault_path=vault, gmail_service=mock_gmail_service)
    item = {
        "id": "msg_news",
        "from": "newsletter@blog.com",
        "subject": "Weekly Digest",
        "date": "2026-02-17",
        "body": "This week's top stories.",
        "labels": ["INBOX"],
    }
    path = watcher.create_action_file(item)
    content = path.read_text()
    assert "priority: low" in content


def test_action_file_has_high_priority_for_vip_sender(vault, mock_gmail_service):
    """Action file should have priority: high for VIP senders."""
    from src.watchers.gmail_watcher import GmailWatcher
    watcher = GmailWatcher(
        vault_path=vault, gmail_service=mock_gmail_service,
        vip_senders=["ceo@company.com"],
    )
    item = {
        "id": "msg_vip",
        "from": "ceo@company.com",
        "subject": "Quick question",
        "date": "2026-02-17",
        "body": "Can you check something?",
        "labels": ["INBOX"],
    }
    path = watcher.create_action_file(item)
    content = path.read_text()
    assert "priority: high" in content
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/watchers/test_gmail_watcher.py -v`
Expected: FAIL — `GmailWatcher.__init__() got an unexpected keyword argument 'vip_senders'`

**Step 3: Wire classify_priority into GmailWatcher**

In `src/watchers/gmail_watcher.py`:

Add import (after line 7):
```python
from src.priority import classify_priority
```

Modify constructor (line 15):
```python
    def __init__(self, vault_path: Path, gmail_service, gmail_filter: str = "is:unread",
                 check_interval: int = 60, vip_senders: list[str] | None = None):
        super().__init__(vault_path, check_interval)
        self.service = gmail_service
        self.gmail_filter = gmail_filter
        self.vip_senders = vip_senders or []
        self._processed_label_id = None
```

Modify `create_action_file()` (line 39-65) — replace hardcoded `priority: normal`:
```python
    def create_action_file(self, item: dict) -> Path:
        slug = slugify(item["subject"])[:50] or "no-subject"
        filename = f"email-{slug}-{item['id'][:8]}.md"
        path = self.needs_action_dir / filename
        priority = classify_priority(
            subject=item["subject"],
            body=item["body"],
            sender=item["from"],
            vip_senders=self.vip_senders,
        )
        content = f"""---
type: email
from: {item['from']}
subject: {item['subject']}
date: {item['date']}
priority: {priority}
gmail_id: {item['id']}
---

# New Email: {item['subject']}

**From:** {item['from']}
**Date:** {item['date']}
**Priority:** {priority}
**Labels:** {', '.join(item.get('labels', []))}

## Body
{item['body']}

## Suggested Actions
- [ ] Reply
- [ ] Forward
- [ ] Archive
"""
        path.write_text(content, encoding="utf-8")
        logger.info(f"Created action file: {path.name} (priority={priority})")
        log_action(
            logs_dir=self.vault_path / "Logs",
            actor="gmail_watcher",
            action="email_detected",
            source=item["id"],
            result=f"action_file_created:{filename}:priority={priority}",
        )
        self.mark_as_processed(item["id"])
        return path
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/watchers/test_gmail_watcher.py -v`
Expected: 9 PASSED

**Step 5: Run full suite**

Run: `python -m pytest tests/ -v`
Expected: All pass

**Step 6: Commit**

```bash
git add src/watchers/gmail_watcher.py tests/watchers/test_gmail_watcher.py
git commit -m "feat: wire classify_priority into GmailWatcher action files"
```

---

### Task 7: Sort `get_pending_actions()` by priority

**Files:**
- Modify: `src/orchestrator.py:33-34` (get_pending_actions method)
- Modify: `tests/test_orchestrator.py`

**Step 1: Write failing tests**

Append to `tests/test_orchestrator.py`:

```python
def test_get_pending_actions_sorted_by_priority(tmp_path):
    """get_pending_actions should return high-priority files before normal, then low."""
    from setup_vault import setup_vault
    from src.orchestrator import Orchestrator

    setup_vault(tmp_path)

    # Create action files with different priorities
    (tmp_path / "Needs_Action" / "email-low.md").write_text(
        "---\npriority: low\n---\n# Low priority email", encoding="utf-8"
    )
    (tmp_path / "Needs_Action" / "email-normal.md").write_text(
        "---\npriority: normal\n---\n# Normal priority email", encoding="utf-8"
    )
    (tmp_path / "Needs_Action" / "email-high.md").write_text(
        "---\npriority: high\n---\n# High priority email", encoding="utf-8"
    )

    orch = Orchestrator(vault_path=tmp_path)
    actions = orch.get_pending_actions()

    assert len(actions) == 3
    assert actions[0].name == "email-high.md"
    assert actions[2].name == "email-low.md"


def test_get_pending_actions_handles_missing_priority(tmp_path):
    """Files without priority frontmatter should be treated as normal."""
    from setup_vault import setup_vault
    from src.orchestrator import Orchestrator

    setup_vault(tmp_path)

    (tmp_path / "Needs_Action" / "email-high.md").write_text(
        "---\npriority: high\n---\n# High", encoding="utf-8"
    )
    (tmp_path / "Needs_Action" / "email-nofm.md").write_text(
        "# No frontmatter email", encoding="utf-8"
    )

    orch = Orchestrator(vault_path=tmp_path)
    actions = orch.get_pending_actions()

    assert len(actions) == 2
    assert actions[0].name == "email-high.md"
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_orchestrator.py::test_get_pending_actions_sorted_by_priority -v`
Expected: FAIL — files returned in alphabetical order, not priority order

**Step 3: Implement priority sorting**

In `src/orchestrator.py`, replace `get_pending_actions()` (lines 33-34):

```python
    def get_pending_actions(self) -> list[Path]:
        priority_order = {"high": 0, "normal": 1, "low": 2}
        files = list(self.needs_action.glob("*.md"))

        def _priority_key(path: Path) -> int:
            fm = parse_frontmatter(path)
            return priority_order.get(fm.get("priority", "normal"), 1)

        return sorted(files, key=_priority_key)
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_orchestrator.py -v`
Expected: All PASSED

**Step 5: Run full suite**

Run: `python -m pytest tests/ -v`
Expected: All pass

**Step 6: Commit**

```bash
git add src/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: sort get_pending_actions by priority (high first)"
```

---

### Task 8: Wire `vip_senders` into `main.py` and update `.env.example`

**Files:**
- Modify: `main.py:36-41` (GmailWatcher constructor)
- Modify: `.env.example`

**Step 1: Add `vip_senders` to GmailWatcher in main.py**

In `main.py`, modify the GmailWatcher constructor call (lines 36-41):

```python
    watcher = GmailWatcher(
        vault_path=cfg.vault_path,
        gmail_service=gmail_service,
        gmail_filter=cfg.gmail_filter,
        check_interval=cfg.gmail_check_interval,
        vip_senders=cfg.vip_senders,
    )
```

**Step 2: Update `.env.example`**

Add after the AUTO_APPROVE_THRESHOLD line:

```
# VIP senders (comma-separated emails that always get high priority)
VIP_SENDERS=
```

**Step 3: Run full suite**

Run: `python -m pytest tests/ -v`
Expected: All pass

**Step 4: Commit**

```bash
git add main.py .env.example
git commit -m "feat: pass vip_senders config to GmailWatcher"
```

---

### Task 9: E2E integration test — priority processing order

**Files:**
- Modify: `tests/test_integration.py`

**Step 1: Write the test**

Append to `tests/test_integration.py`:

```python
def test_priority_processing_order(tmp_path):
    """End-to-end: high-priority email should be processed before normal-priority."""
    from setup_vault import setup_vault
    from src.watchers.gmail_watcher import GmailWatcher
    from src.orchestrator import Orchestrator

    setup_vault(tmp_path)

    service = MagicMock()
    service.users().messages().list.return_value.execute.return_value = {
        "messages": [
            {"id": "msg_normal", "threadId": "t1"},
            {"id": "msg_urgent", "threadId": "t2"},
        ]
    }

    def get_message(userId, id, format):
        mock = MagicMock()
        if id == "msg_normal":
            mock.execute.return_value = {
                "id": "msg_normal",
                "payload": {
                    "headers": [
                        {"name": "From", "value": "colleague@example.com"},
                        {"name": "Subject", "value": "Weekly Report"},
                        {"name": "Date", "value": "2026-02-17"},
                    ],
                    "body": {"data": "SGVyZSBpcyB0aGUgd2Vla2x5IHJlcG9ydA=="},
                },
                "labelIds": ["INBOX"],
            }
        else:
            mock.execute.return_value = {
                "id": "msg_urgent",
                "payload": {
                    "headers": [
                        {"name": "From", "value": "boss@example.com"},
                        {"name": "Subject", "value": "URGENT: Need response now"},
                        {"name": "Date", "value": "2026-02-17"},
                    ],
                    "body": {"data": "UGxlYXNlIHJlc3BvbmQgQVNBUA=="},
                },
                "labelIds": ["INBOX"],
            }
        return mock

    service.users().messages().get.side_effect = get_message
    service.users().labels().list.return_value.execute.return_value = {
        "labels": [{"id": "L1", "name": "Processed-by-FTE"}]
    }

    # Step 1: Watcher detects both emails
    watcher = GmailWatcher(vault_path=tmp_path, gmail_service=service)
    count = watcher.run_once()
    assert count == 2

    # Step 2: Verify priority tags
    action_files = list((tmp_path / "Needs_Action").glob("*.md"))
    assert len(action_files) == 2

    priorities = {}
    for f in action_files:
        content = f.read_text()
        if "msg_urgent" in f.name or "urgent" in f.name.lower():
            assert "priority: high" in content
            priorities["high"] = f
        else:
            assert "priority: normal" in content
            priorities["normal"] = f

    # Step 3: Orchestrator should process high-priority first
    orch = Orchestrator(vault_path=tmp_path)
    pending = orch.get_pending_actions()
    first_file_content = pending[0].read_text()
    assert "priority: high" in first_file_content
```

**Step 2: Run test to verify it passes**

Run: `python -m pytest tests/test_integration.py::test_priority_processing_order -v`
Expected: PASS

**Step 3: Run full suite**

Run: `python -m pytest tests/ -v`
Expected: All pass

**Step 4: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add E2E integration test for priority processing order"
```

---

### Task 10: Update README for Obsidian tier

**Files:**
- Modify: `README.md`

**Step 1: Update README**

Changes:
1. Title: `# Digital FTE — Obsidian Tier`
2. Tagline: add "with smart email prioritization"
3. Architecture diagram: add priority classification step
4. Layer 1 description: mention priority classification
5. Usage list: add priority classification step
6. Configuration table: add `VIP_SENDERS` row
7. Tier declaration: update for Obsidian

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update README for Obsidian tier with smart prioritization"
```

---

### Task 11: Final verification

**Step 1: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: All tests pass (should be ~106+ tests)

**Step 2: Verify git log**

Run: `git log --oneline feature/digital-fte-obsidian ^master`
Expected: ~10 commits for the Obsidian tier

**Step 3: Create PHR if needed, then offer to commit and create PR**
