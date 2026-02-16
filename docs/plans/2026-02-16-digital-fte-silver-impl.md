# Digital FTE Silver — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete the email loop — Claude drafts replies in plan files, humans approve in Obsidian, and the agent sends replies via Gmail API with a daily send limit.

**Architecture:** Extend the existing Orchestrator with Gmail send capability. New `gmail_sender.py` module handles message building and threading. `utils.py` gains frontmatter parsing and reply extraction helpers. Auth gets the `gmail.send` scope. No new abstractions — direct extension of Approach A.

**Tech Stack:** Python 3.13, google-api-python-client (Gmail send), pyyaml (frontmatter parsing), pytest

---

### Task 1: Add `daily_send_limit` to Config

**Files:**
- Modify: `tests/test_config.py`
- Modify: `src/config.py`
- Modify: `.env.example`

**Step 1: Write the failing test**

Add to `tests/test_config.py`:

```python
def test_config_loads_daily_send_limit(monkeypatch):
    """Config should read DAILY_SEND_LIMIT from environment."""
    monkeypatch.setenv("DAILY_SEND_LIMIT", "50")
    from src.config import load_config
    cfg = load_config()
    assert cfg.daily_send_limit == 50


def test_config_daily_send_limit_default(monkeypatch):
    """Config should default daily_send_limit to 20."""
    monkeypatch.delenv("DAILY_SEND_LIMIT", raising=False)
    from src.config import load_config
    cfg = load_config()
    assert cfg.daily_send_limit == 20
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — `Config` has no `daily_send_limit` field

**Step 3: Implement the config change**

In `src/config.py`, add `daily_send_limit: int` to the `Config` dataclass and load it in `load_config()`:

```python
@dataclass
class Config:
    vault_path: Path
    gmail_check_interval: int
    gmail_filter: str
    claude_model: str
    log_level: str
    daily_send_limit: int
```

In `load_config()`, add:

```python
    daily_send_limit=int(os.getenv("DAILY_SEND_LIMIT", "20")),
```

In `.env.example`, append:

```
# Maximum emails the agent will send per day
DAILY_SEND_LIMIT=20
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add tests/test_config.py src/config.py .env.example
git commit -m "feat: add daily_send_limit to config"
```

---

### Task 2: Add `parse_frontmatter()` and `extract_reply_block()` to utils

**Files:**
- Modify: `tests/test_utils.py`
- Modify: `src/utils.py`

**Step 1: Write failing tests for `parse_frontmatter`**

Add to `tests/test_utils.py`:

```python
def test_parse_frontmatter_extracts_yaml(tmp_path):
    """parse_frontmatter should extract YAML between --- delimiters."""
    from src.utils import parse_frontmatter
    f = tmp_path / "test.md"
    f.write_text("---\naction: reply\nto: bob@test.com\nsubject: Re: Hello\n---\n\n# Plan\nSome content.")
    result = parse_frontmatter(f)
    assert result["action"] == "reply"
    assert result["to"] == "bob@test.com"
    assert result["subject"] == "Re: Hello"


def test_parse_frontmatter_returns_empty_on_no_frontmatter(tmp_path):
    """parse_frontmatter should return empty dict when no YAML block exists."""
    from src.utils import parse_frontmatter
    f = tmp_path / "test.md"
    f.write_text("# Just a heading\nNo frontmatter here.")
    result = parse_frontmatter(f)
    assert result == {}
```

**Step 2: Write failing tests for `extract_reply_block`**

Add to `tests/test_utils.py`:

```python
def test_extract_reply_block(tmp_path):
    """extract_reply_block should return text between BEGIN/END REPLY markers."""
    from src.utils import extract_reply_block
    f = tmp_path / "plan.md"
    f.write_text(
        "---\naction: reply\n---\n\n# Plan\n\n## Reply Draft\n"
        "---BEGIN REPLY---\nHi Bob,\n\nThanks for your email.\n\nBest regards\n---END REPLY---\n"
    )
    result = extract_reply_block(f)
    assert result == "Hi Bob,\n\nThanks for your email.\n\nBest regards"


def test_extract_reply_block_returns_none_when_missing(tmp_path):
    """extract_reply_block should return None when no reply block exists."""
    from src.utils import extract_reply_block
    f = tmp_path / "plan.md"
    f.write_text("---\naction: reply\n---\n\n# Plan\nNo reply block here.")
    result = extract_reply_block(f)
    assert result is None
```

**Step 3: Run tests to verify they fail**

Run: `pytest tests/test_utils.py -v`
Expected: FAIL — functions not defined

**Step 4: Implement both functions**

Add to `src/utils.py`:

```python
import yaml


def parse_frontmatter(file_path: Path) -> dict:
    """Extract YAML frontmatter from a markdown file."""
    text = file_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    try:
        return yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return {}


def extract_reply_block(file_path: Path) -> str | None:
    """Extract reply text between ---BEGIN REPLY--- and ---END REPLY--- markers."""
    text = file_path.read_text(encoding="utf-8")
    begin = "---BEGIN REPLY---"
    end = "---END REPLY---"
    start_idx = text.find(begin)
    end_idx = text.find(end)
    if start_idx == -1 or end_idx == -1:
        return None
    return text[start_idx + len(begin):end_idx].strip()
```

Note: `yaml` is already in `requirements.txt` (pyyaml). Add the `import yaml` at the top of `src/utils.py`.

**Step 5: Run tests to verify they pass**

Run: `pytest tests/test_utils.py -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add tests/test_utils.py src/utils.py
git commit -m "feat: add parse_frontmatter and extract_reply_block helpers"
```

---

### Task 3: Add `gmail.send` scope to auth

**Files:**
- Modify: `src/auth.py`

**Step 1: Update the SCOPES constant**

In `src/auth.py`, change line 11:

From:
```python
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
```

To:
```python
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]
```

**Step 2: Verify existing auth tests still pass**

Run: `pytest tests/ -v`
Expected: ALL PASS (no auth tests touch the actual scope constant, they use mocks)

**Step 3: Commit**

```bash
git add src/auth.py
git commit -m "feat: add gmail.send scope to OAuth credentials"
```

---

### Task 4: Create Gmail sender module

**Files:**
- Create: `tests/test_gmail_sender.py`
- Create: `src/gmail_sender.py`

**Step 1: Write failing tests**

Create `tests/test_gmail_sender.py`:

```python
"""Tests for Gmail reply sending."""
import base64
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.gmail_sender import send_reply, check_send_limit, increment_send_count


@pytest.fixture
def gmail_service():
    service = MagicMock()
    # Mock fetching original message for threadId and Message-ID
    service.users().messages().get.return_value.execute.return_value = {
        "id": "orig_msg_id",
        "threadId": "thread_123",
        "payload": {
            "headers": [
                {"name": "Message-ID", "value": "<original@example.com>"},
            ],
        },
    }
    # Mock sending
    service.users().messages().send.return_value.execute.return_value = {
        "id": "sent_msg_id",
        "threadId": "thread_123",
    }
    return service


def test_send_reply_calls_gmail_send(gmail_service):
    """send_reply should call Gmail API to send the message."""
    result = send_reply(
        gmail_service=gmail_service,
        gmail_id="orig_msg_id",
        to="bob@test.com",
        subject="Re: Hello",
        body="Thanks for your email.",
    )
    gmail_service.users().messages().send.assert_called_once()
    assert result["id"] == "sent_msg_id"
    assert result["threadId"] == "thread_123"


def test_send_reply_includes_thread_id(gmail_service):
    """send_reply should include threadId for proper Gmail threading."""
    send_reply(
        gmail_service=gmail_service,
        gmail_id="orig_msg_id",
        to="bob@test.com",
        subject="Re: Hello",
        body="Thanks.",
    )
    call_args = gmail_service.users().messages().send.call_args
    send_body = call_args[1]["body"] if "body" in call_args[1] else call_args[0][0]
    assert send_body["threadId"] == "thread_123"


def test_send_reply_builds_valid_mime(gmail_service):
    """send_reply should build a base64-encoded MIME message."""
    send_reply(
        gmail_service=gmail_service,
        gmail_id="orig_msg_id",
        to="bob@test.com",
        subject="Re: Hello",
        body="Thanks.",
    )
    call_args = gmail_service.users().messages().send.call_args
    send_body = call_args[1]["body"] if "body" in call_args[1] else call_args[0][0]
    # raw should be a base64url-encoded string
    raw = send_body["raw"]
    decoded = base64.urlsafe_b64decode(raw).decode("utf-8")
    assert "To: bob@test.com" in decoded
    assert "Subject: Re: Hello" in decoded
    assert "Thanks." in decoded
    assert "In-Reply-To: <original@example.com>" in decoded


def test_check_send_limit_under_limit(tmp_path):
    """check_send_limit should return True when under the daily limit."""
    assert check_send_limit(logs_dir=tmp_path, limit=20) is True


def test_check_send_limit_at_limit(tmp_path):
    """check_send_limit should return False when at the daily limit."""
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    count_file = tmp_path / f".send_count_{today}.json"
    count_file.write_text(json.dumps({"count": 20}))
    assert check_send_limit(logs_dir=tmp_path, limit=20) is False


def test_increment_send_count(tmp_path):
    """increment_send_count should increase the daily counter."""
    increment_send_count(logs_dir=tmp_path)
    increment_send_count(logs_dir=tmp_path)

    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    count_file = tmp_path / f".send_count_{today}.json"
    data = json.loads(count_file.read_text())
    assert data["count"] == 2
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_gmail_sender.py -v`
Expected: FAIL — module not found

**Step 3: Implement `src/gmail_sender.py`**

Create `src/gmail_sender.py`:

```python
"""Gmail reply sender — builds and sends threaded email replies."""
import base64
import json
import logging
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path

logger = logging.getLogger("digital_fte.gmail_sender")


def send_reply(gmail_service, gmail_id: str, to: str, subject: str, body: str) -> dict:
    """Send a reply to an existing email thread.

    Fetches the original message to get threadId and Message-ID,
    builds a MIME message with proper threading headers, and sends it.
    """
    # Fetch original message for threading info
    original = gmail_service.users().messages().get(
        userId="me", id=gmail_id, format="metadata",
        metadataHeaders=["Message-ID"],
    ).execute()

    thread_id = original["threadId"]
    headers = {h["name"]: h["value"] for h in original.get("payload", {}).get("headers", [])}
    message_id = headers.get("Message-ID", "")

    # Build MIME message
    mime = MIMEText(body)
    mime["To"] = to
    mime["Subject"] = subject
    if message_id:
        mime["In-Reply-To"] = message_id
        mime["References"] = message_id

    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode("utf-8")

    result = gmail_service.users().messages().send(
        userId="me",
        body={"raw": raw, "threadId": thread_id},
    ).execute()

    logger.info(f"Reply sent to {to} (message_id={result['id']}, thread={thread_id})")
    return result


def check_send_limit(logs_dir: Path, limit: int) -> bool:
    """Return True if under the daily send limit, False if at/over."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    count_file = logs_dir / f".send_count_{today}.json"
    if not count_file.exists():
        return True
    data = json.loads(count_file.read_text())
    return data.get("count", 0) < limit


def increment_send_count(logs_dir: Path) -> int:
    """Increment the daily send counter. Returns new count."""
    logs_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    count_file = logs_dir / f".send_count_{today}.json"
    count = 0
    if count_file.exists():
        data = json.loads(count_file.read_text())
        count = data.get("count", 0)
    count += 1
    count_file.write_text(json.dumps({"count": count}))
    return count
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_gmail_sender.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add tests/test_gmail_sender.py src/gmail_sender.py
git commit -m "feat: add Gmail reply sender with send limit tracking"
```

---

### Task 5: Extend Orchestrator with reply execution

**Files:**
- Modify: `tests/test_orchestrator.py`
- Modify: `src/orchestrator.py`

**Step 1: Write failing tests for reply execution**

Add to `tests/test_orchestrator.py`:

```python
def make_reply_plan(vault, gmail_id="msg_abc123", to="bob@test.com", subject="Re: Hello"):
    """Helper: create an approved plan file with a reply block."""
    content = f"""---
source: email-test.md
created: 2026-02-16T10:00:00Z
status: pending_approval
action: reply
gmail_id: {gmail_id}
to: {to}
subject: "{subject}"
---

# Plan: email-test

## Analysis
General greeting.

## Reply Draft
---BEGIN REPLY---
Hi Bob,

Thanks for reaching out.

Best regards
---END REPLY---
"""
    path = vault / "Approved" / "plan-test-reply.md"
    path.write_text(content)
    return path


def test_orchestrator_sends_reply_on_approved(vault):
    """execute_approved should call send_reply when action is reply."""
    from src.orchestrator import Orchestrator
    mock_gmail = MagicMock()
    mock_gmail.users().messages().get.return_value.execute.return_value = {
        "id": "msg_abc123",
        "threadId": "t1",
        "payload": {"headers": [{"name": "Message-ID", "value": "<orig@test.com>"}]},
    }
    mock_gmail.users().messages().send.return_value.execute.return_value = {
        "id": "sent_1", "threadId": "t1",
    }
    orch = Orchestrator(vault_path=vault, gmail_service=mock_gmail)
    plan = make_reply_plan(vault)
    orch.execute_approved(plan)
    mock_gmail.users().messages().send.assert_called_once()
    assert not plan.exists()
    assert (vault / "Done" / "plan-test-reply.md").exists()


def test_orchestrator_skips_send_when_no_action(vault):
    """execute_approved should just move to Done when no action field."""
    from src.orchestrator import Orchestrator
    mock_gmail = MagicMock()
    orch = Orchestrator(vault_path=vault, gmail_service=mock_gmail)
    approved_file = vault / "Approved" / "plan-no-action.md"
    approved_file.write_text("---\nsource: email-test.md\nstatus: pending_approval\n---\n\n# Plan\nJust analysis.")
    orch.execute_approved(approved_file)
    mock_gmail.users().messages().send.assert_not_called()
    assert (vault / "Done" / "plan-no-action.md").exists()


def test_orchestrator_respects_daily_send_limit(vault):
    """execute_approved should skip sending when daily limit is reached."""
    from src.orchestrator import Orchestrator
    mock_gmail = MagicMock()
    orch = Orchestrator(vault_path=vault, gmail_service=mock_gmail, daily_send_limit=0)
    plan = make_reply_plan(vault)
    orch.execute_approved(plan)
    mock_gmail.users().messages().send.assert_not_called()
    # File should remain in Approved (not moved to Done)
    assert plan.exists()


def test_orchestrator_handles_missing_reply_block(vault):
    """execute_approved should move to Done with failure when reply block is missing."""
    from src.orchestrator import Orchestrator
    mock_gmail = MagicMock()
    orch = Orchestrator(vault_path=vault, gmail_service=mock_gmail)
    approved_file = vault / "Approved" / "plan-bad-reply.md"
    approved_file.write_text("---\naction: reply\ngmail_id: msg1\nto: a@b.com\nsubject: Re: X\n---\n\n# Plan\nNo reply block!")
    orch.execute_approved(approved_file)
    mock_gmail.users().messages().send.assert_not_called()
    assert (vault / "Done" / "plan-bad-reply.md").exists()
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_orchestrator.py -v`
Expected: FAIL — `Orchestrator.__init__` doesn't accept `gmail_service`

**Step 3: Update the Orchestrator**

Modify `src/orchestrator.py`:

```python
"""Orchestrator — processes action files using Claude and manages the approval pipeline."""
import logging
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from src.gmail_sender import send_reply, check_send_limit, increment_send_count
from src.utils import log_action, parse_frontmatter, extract_reply_block

logger = logging.getLogger("digital_fte.orchestrator")


class Orchestrator:
    def __init__(self, vault_path: Path, claude_model: str = "claude-sonnet-4-5-20250929",
                 gmail_service=None, daily_send_limit: int = 20):
        self.vault_path = vault_path
        self.claude_model = claude_model
        self.gmail_service = gmail_service
        self.daily_send_limit = daily_send_limit
        self.needs_action = vault_path / "Needs_Action"
        self.plans = vault_path / "Plans"
        self.pending_approval = vault_path / "Pending_Approval"
        self.approved = vault_path / "Approved"
        self.done = vault_path / "Done"
        self.logs = vault_path / "Logs"
        self.handbook_path = vault_path / "Company_Handbook.md"

    def get_pending_actions(self) -> list[Path]:
        return sorted(self.needs_action.glob("*.md"))

    def get_approved_actions(self) -> list[Path]:
        return sorted(self.approved.glob("*.md"))

    def process_action(self, action_file: Path) -> Path:
        logger.info(f"Processing: {action_file.name}")
        action_content = action_file.read_text(encoding="utf-8")
        handbook = ""
        if self.handbook_path.exists():
            handbook = self.handbook_path.read_text(encoding="utf-8")

        # Extract email metadata for reply context
        metadata = parse_frontmatter(action_file)
        claude_response = self._invoke_claude(action_content, handbook, metadata)

        now = datetime.now(timezone.utc).isoformat()
        plan_name = action_file.name.replace("email-", "plan-")

        # Build frontmatter — include reply fields if Claude generated a reply
        fm_lines = [
            f"source: {action_file.name}",
            f"created: {now}",
            "status: pending_approval",
        ]
        if "---BEGIN REPLY---" in claude_response:
            fm_lines.append("action: reply")
            fm_lines.append(f"gmail_id: {metadata.get('gmail_id', '')}")
            fm_lines.append(f"to: {metadata.get('from', '')}")
            subject = metadata.get("subject", "")
            if not subject.startswith("Re:"):
                subject = f"Re: {subject}"
            fm_lines.append(f'subject: "{subject}"')

        frontmatter = "\n".join(fm_lines)
        plan_content = f"""---
{frontmatter}
---

# Plan: {action_file.stem}

{claude_response}
"""
        plan_path = self.pending_approval / plan_name
        plan_path.write_text(plan_content, encoding="utf-8")
        action_file.unlink()
        log_action(
            logs_dir=self.logs,
            actor="orchestrator",
            action="plan_created",
            source=action_file.name,
            result=f"pending_approval:{plan_name}",
        )
        logger.info(f"Plan created: {plan_path.name} (awaiting approval)")
        return plan_path

    def execute_approved(self, approved_file: Path) -> Path:
        logger.info(f"Executing approved action: {approved_file.name}")
        metadata = parse_frontmatter(approved_file)

        if metadata.get("action") == "reply":
            # Check daily send limit
            if not check_send_limit(self.logs, self.daily_send_limit):
                logger.warning(f"Daily send limit ({self.daily_send_limit}) reached. Skipping: {approved_file.name}")
                return approved_file

            # Extract reply body
            reply_body = extract_reply_block(approved_file)
            if reply_body is None:
                logger.error(f"No reply block found in {approved_file.name}. Moving to Done as failed.")
                dest = self.done / approved_file.name
                shutil.move(str(approved_file), str(dest))
                log_action(
                    logs_dir=self.logs,
                    actor="orchestrator",
                    action="reply_failed",
                    source=approved_file.name,
                    result="missing_reply_block",
                )
                return dest

            # Send the reply
            try:
                send_reply(
                    gmail_service=self.gmail_service,
                    gmail_id=metadata["gmail_id"],
                    to=metadata["to"],
                    subject=metadata.get("subject", ""),
                    body=reply_body,
                )
                increment_send_count(self.logs)
                log_action(
                    logs_dir=self.logs,
                    actor="orchestrator",
                    action="email_sent",
                    source=approved_file.name,
                    result=f"reply_to:{metadata['to']}",
                )
            except Exception as e:
                logger.error(f"Failed to send reply for {approved_file.name}: {e}")
                log_action(
                    logs_dir=self.logs,
                    actor="orchestrator",
                    action="send_failed",
                    source=approved_file.name,
                    result=str(e),
                )
                return approved_file

        dest = self.done / approved_file.name
        shutil.move(str(approved_file), str(dest))
        log_action(
            logs_dir=self.logs,
            actor="orchestrator",
            action="executed",
            source=approved_file.name,
            result="moved_to_done",
        )
        logger.info(f"Completed: {dest.name}")
        return dest

    def _invoke_claude(self, action_content: str, handbook: str, metadata: dict = None) -> str:
        prompt = f"""You are a Digital FTE (AI employee). Analyze the following action item and create a plan.

## Company Handbook
{handbook}

## Action Item
{action_content}

## Instructions
1. Analyze the action item
2. Determine what needs to be done
3. List recommended actions
4. Identify which actions require human approval
5. If a reply email is appropriate, draft the full reply text

Respond with:
## Analysis
[Your analysis]

## Recommended Actions
[Numbered list]

## Requires Approval
[Checklist of items needing human approval]

## Reply Draft
If a reply is needed, include the reply text between these exact markers:
---BEGIN REPLY---
[Your drafted reply text here]
---END REPLY---

If no reply is needed, omit the Reply Draft section entirely.
"""
        try:
            result = subprocess.run(
                ["claude", "--print", "--model", self.claude_model, prompt],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logger.error(f"Claude error: {result.stderr}")
                return "## Analysis\nClaude processing failed. Manual review required.\n\n## Requires Approval\n- [ ] Manual review needed"
        except FileNotFoundError:
            logger.error("Claude CLI not found. Is Claude Code installed?")
            return "## Analysis\nClaude CLI not available. Manual review required.\n\n## Requires Approval\n- [ ] Manual review needed"
        except subprocess.TimeoutExpired:
            logger.error("Claude timed out after 120 seconds")
            return "## Analysis\nClaude timed out. Manual review required.\n\n## Requires Approval\n- [ ] Manual review needed"
```

**Step 4: Fix existing tests**

The existing `test_orchestrator_moves_approved_to_done` test still works because `gmail_service=None` is the default. Verify:

Run: `pytest tests/test_orchestrator.py -v`
Expected: ALL PASS (new + existing)

**Step 5: Commit**

```bash
git add tests/test_orchestrator.py src/orchestrator.py
git commit -m "feat: extend orchestrator with Gmail reply execution and send limits"
```

---

### Task 6: Update `main.py` to wire Gmail service into Orchestrator

**Files:**
- Modify: `main.py`

**Step 1: Update main.py**

Pass `gmail_service` and `daily_send_limit` to the Orchestrator:

In `main.py`, change the Orchestrator instantiation from:

```python
    orchestrator = Orchestrator(
        vault_path=cfg.vault_path,
        claude_model=cfg.claude_model,
    )
```

To:

```python
    orchestrator = Orchestrator(
        vault_path=cfg.vault_path,
        claude_model=cfg.claude_model,
        gmail_service=gmail_service,
        daily_send_limit=cfg.daily_send_limit,
    )
```

And update the startup log message from:

```python
    logger.info(
        f"Digital FTE started — watching Gmail every {cfg.gmail_check_interval}s "
        f"(filter: {cfg.gmail_filter})"
    )
```

To:

```python
    logger.info(
        f"Digital FTE started — watching Gmail every {cfg.gmail_check_interval}s "
        f"(filter: {cfg.gmail_filter}, send_limit: {cfg.daily_send_limit}/day)"
    )
```

**Step 2: Run all tests**

Run: `pytest tests/ -v`
Expected: ALL PASS

**Step 3: Commit**

```bash
git add main.py
git commit -m "feat: wire Gmail service and send limit into orchestrator"
```

---

### Task 7: Extend integration test for full reply flow

**Files:**
- Modify: `tests/test_integration.py`

**Step 1: Write the integration test**

Add to `tests/test_integration.py`:

```python
def test_full_reply_pipeline(tmp_path):
    """End-to-end: email in → Claude plan with reply → approve → send → done."""
    from setup_vault import setup_vault
    from src.watchers.gmail_watcher import GmailWatcher
    from src.orchestrator import Orchestrator

    setup_vault(tmp_path)

    service = MagicMock()
    service.users().messages().list.return_value.execute.return_value = {
        "messages": [{"id": "msg_reply_e2e", "threadId": "t_reply"}]
    }
    service.users().messages().get.return_value.execute.return_value = {
        "id": "msg_reply_e2e",
        "threadId": "t_reply",
        "payload": {
            "headers": [
                {"name": "From", "value": "client@example.com"},
                {"name": "Subject", "value": "Invoice #99"},
                {"name": "Date", "value": "2026-02-16"},
                {"name": "Message-ID", "value": "<inv99@example.com>"},
            ],
            "body": {"data": "UGxlYXNlIHBheSBpbnZvaWNlICM5OQ=="},
        },
        "labelIds": ["INBOX"],
    }
    service.users().labels().list.return_value.execute.return_value = {
        "labels": [{"id": "L1", "name": "Processed-by-FTE"}]
    }
    service.users().messages().send.return_value.execute.return_value = {
        "id": "sent_reply_1", "threadId": "t_reply",
    }

    # Step 1: Watcher detects email
    watcher = GmailWatcher(vault_path=tmp_path, gmail_service=service)
    count = watcher.run_once()
    assert count == 1
    action_files = list((tmp_path / "Needs_Action").glob("*.md"))
    assert len(action_files) == 1

    # Step 2: Orchestrator processes — Claude returns a reply draft
    orch = Orchestrator(vault_path=tmp_path, gmail_service=service, daily_send_limit=20)
    claude_reply = (
        "## Analysis\nInvoice payment request.\n\n"
        "## Recommended Actions\n1. Acknowledge and confirm payment timeline\n\n"
        "## Requires Approval\n- [ ] Send reply\n\n"
        "## Reply Draft\n"
        "---BEGIN REPLY---\n"
        "Hi,\n\nThank you for Invoice #99. Payment will be processed within 5 business days.\n\n"
        "Best regards\n"
        "---END REPLY---"
    )
    with patch.object(orch, "_invoke_claude") as mock_claude:
        mock_claude.return_value = claude_reply
        plan_path = orch.process_action(action_files[0])

    assert plan_path.parent.name == "Pending_Approval"
    plan_content = plan_path.read_text()
    assert "action: reply" in plan_content
    assert "---BEGIN REPLY---" in plan_content

    # Step 3: Simulate human approval
    approved_path = tmp_path / "Approved" / plan_path.name
    shutil.move(str(plan_path), str(approved_path))

    # Step 4: Orchestrator sends the reply
    done_path = orch.execute_approved(approved_path)
    assert done_path.parent.name == "Done"
    assert not approved_path.exists()
    service.users().messages().send.assert_called_once()
```

**Step 2: Run tests to verify they pass**

Run: `pytest tests/test_integration.py -v`
Expected: ALL PASS

**Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add end-to-end integration test for reply pipeline"
```

---

### Task 8: Update README

**Files:**
- Modify: `README.md`

**Step 1: Update the README**

Update the tier declaration and add Silver tier info:

1. Change the title from `# Digital FTE — Bronze Tier` to `# Digital FTE — Silver Tier`

2. Update the tagline to mention reply sending:
   > Your life and business on autopilot. Local-first, agent-driven, human-in-the-loop. Now with email replies.

3. Update the architecture diagram to show the reply path:
   ```
   Gmail ──► Gmail Watcher ──► vault/Needs_Action/
                                       │
                               Orchestrator + Claude
                                       │
                               vault/Pending_Approval/
                                       │
                                 Human reviews
                                       │
                               vault/Approved/ ──► Gmail Reply ──► vault/Done/
   ```

4. Add `DAILY_SEND_LIMIT` to the configuration table:
   | `DAILY_SEND_LIMIT` | `20` | Max emails sent per day |

5. Update the "The agent will" list to include:
   > 4. Wait for you to review — move approved files to `vault/Approved/`
   > 5. **Send email replies** for approved plans that include a reply draft
   > 6. Execute and archive to `vault/Done/`

6. Update the tier declaration:
   > **Silver Tier** — Gmail watcher with reply sending, Claude-drafted responses, daily send limits, Obsidian vault with approval pipeline.

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update README for Silver tier with reply sending"
```

---

### Task 9: Final verification

**Step 1: Run the full test suite**

Run: `pytest tests/ -v`
Expected: ALL PASS

**Step 2: Check for lint/import issues**

Run: `python -c "from src.orchestrator import Orchestrator; from src.gmail_sender import send_reply; print('All imports OK')"`
Expected: `All imports OK`

**Step 3: Merge commit**

```bash
git add -A
git commit -m "feat: Digital FTE Silver tier — Gmail reply execution with send limits"
```
