# Digital FTE Bronze — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an autonomous AI agent that monitors Gmail, creates action files in an Obsidian vault, and uses Claude Code to analyze emails and generate plans with human-in-the-loop approval.

**Architecture:** Single Python project (monolith). Gmail watcher polls for unread emails and drops markdown files into an Obsidian vault's `Needs_Action/` folder. An orchestrator watches that folder, invokes Claude Code to process each item, and routes results through a folder-based approval pipeline (`Plans → Pending_Approval → Approved → Done`).

**Tech Stack:** Python 3.13, google-api-python-client, google-auth-oauthlib, watchdog, python-dotenv, pyyaml, pytest

---

### Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `src/__init__.py`
- Create: `src/watchers/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/watchers/__init__.py`

**Step 1: Create requirements.txt**

```txt
google-api-python-client==2.166.0
google-auth-oauthlib==1.2.1
google-auth-httplib2==0.2.0
watchdog==6.0.0
python-dotenv==1.1.0
pyyaml==6.0.2
pytest==8.3.5
pytest-mock==3.14.0
```

**Step 2: Create .env.example**

```
# Obsidian vault path (relative or absolute)
VAULT_PATH=./vault

# Gmail polling interval in seconds
GMAIL_CHECK_INTERVAL=60

# Gmail search filter
GMAIL_FILTER=is:unread

# Claude model for orchestrator
CLAUDE_MODEL=claude-sonnet-4-5-20250929

# Logging level
LOG_LEVEL=INFO
```

**Step 3: Create .gitignore**

Add entries for: `.env`, `credentials/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `vault/Logs/`, `*.egg-info/`, `dist/`, `build/`

**Step 4: Create package init files**

Empty `__init__.py` files in `src/`, `src/watchers/`, `tests/`, `tests/watchers/`

**Step 5: Install dependencies**

Run: `pip install -r requirements.txt`

**Step 6: Commit**

```bash
git add requirements.txt .env.example .gitignore src/__init__.py src/watchers/__init__.py tests/__init__.py tests/watchers/__init__.py
git commit -m "chore: project scaffolding with dependencies and gitignore"
```

---

### Task 2: Configuration Module

**Files:**
- Create: `tests/test_config.py`
- Create: `src/config.py`
- Create: `.env` (local only, gitignored)

**Step 1: Write the failing test**

```python
# tests/test_config.py
import os
import pytest


def test_config_loads_vault_path(tmp_path, monkeypatch):
    """Config should read VAULT_PATH from environment."""
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    from src.config import load_config
    cfg = load_config()
    assert cfg.vault_path == tmp_path


def test_config_defaults(monkeypatch):
    """Config should provide sensible defaults when env vars missing."""
    monkeypatch.delenv("VAULT_PATH", raising=False)
    monkeypatch.delenv("GMAIL_CHECK_INTERVAL", raising=False)
    monkeypatch.delenv("GMAIL_FILTER", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    from src.config import load_config
    cfg = load_config()
    assert cfg.vault_path.name == "vault"
    assert cfg.gmail_check_interval == 60
    assert cfg.gmail_filter == "is:unread"
    assert cfg.log_level == "INFO"


def test_config_gmail_interval_from_env(monkeypatch):
    """Config should parse GMAIL_CHECK_INTERVAL as int."""
    monkeypatch.setenv("GMAIL_CHECK_INTERVAL", "30")
    from src.config import load_config
    cfg = load_config()
    assert cfg.gmail_check_interval == 30
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.config'`

**Step 3: Write minimal implementation**

```python
# src/config.py
from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


@dataclass
class Config:
    vault_path: Path
    gmail_check_interval: int
    gmail_filter: str
    claude_model: str
    log_level: str


def load_config() -> Config:
    """Load configuration from environment variables with defaults."""
    load_dotenv()
    return Config(
        vault_path=Path(os.getenv("VAULT_PATH", "./vault")).resolve(),
        gmail_check_interval=int(os.getenv("GMAIL_CHECK_INTERVAL", "60")),
        gmail_filter=os.getenv("GMAIL_FILTER", "is:unread"),
        claude_model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5-20250929"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_config.py -v`
Expected: 3 passed

**Step 5: Create local .env file**

Copy `.env.example` to `.env` (this stays local, gitignored).

**Step 6: Commit**

```bash
git add tests/test_config.py src/config.py
git commit -m "feat: add configuration module with env var loading and defaults"
```

---

### Task 3: Logging Utilities

**Files:**
- Create: `tests/test_utils.py`
- Create: `src/utils.py`

**Step 1: Write the failing test**

```python
# tests/test_utils.py
import json
from datetime import datetime, timezone
from pathlib import Path


def test_log_action_creates_daily_log_file(tmp_path):
    """log_action should create a JSON log file named YYYY-MM-DD.json."""
    from src.utils import log_action
    log_action(
        logs_dir=tmp_path,
        actor="gmail_watcher",
        action="email_detected",
        source="msg_123",
        result="action_file_created",
    )
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = tmp_path / f"{today}.json"
    assert log_file.exists()
    entries = json.loads(log_file.read_text())
    assert len(entries) == 1
    assert entries[0]["actor"] == "gmail_watcher"
    assert entries[0]["action"] == "email_detected"


def test_log_action_appends_to_existing(tmp_path):
    """log_action should append to existing daily log, not overwrite."""
    from src.utils import log_action
    log_action(logs_dir=tmp_path, actor="a", action="first", source="s", result="r")
    log_action(logs_dir=tmp_path, actor="b", action="second", source="s", result="r")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entries = json.loads((tmp_path / f"{today}.json").read_text())
    assert len(entries) == 2


def test_slugify():
    """slugify should produce filesystem-safe names."""
    from src.utils import slugify
    assert slugify("Re: Invoice #1234!") == "re-invoice-1234"
    assert slugify("  Hello World  ") == "hello-world"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_utils.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/utils.py
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure and return the application logger."""
    logger = logging.getLogger("digital_fte")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def log_action(
    logs_dir: Path,
    actor: str,
    action: str,
    source: str,
    result: str,
) -> None:
    """Append a structured log entry to the daily JSON log file."""
    logs_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = logs_dir / f"{today}.json"

    entries = []
    if log_file.exists():
        entries = json.loads(log_file.read_text())

    entries.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "action": action,
        "source": source,
        "result": result,
    })
    log_file.write_text(json.dumps(entries, indent=2))


def slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_utils.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add tests/test_utils.py src/utils.py
git commit -m "feat: add logging utilities and slugify helper"
```

---

### Task 4: Vault Initialization

**Files:**
- Create: `tests/test_setup_vault.py`
- Create: `setup_vault.py`
- Create: `vault/Company_Handbook.md` (generated by script)

**Step 1: Write the failing test**

```python
# tests/test_setup_vault.py
from pathlib import Path


def test_setup_vault_creates_all_folders(tmp_path):
    """setup_vault should create all required vault subdirectories."""
    from setup_vault import setup_vault
    setup_vault(tmp_path)
    expected = [
        "Needs_Action", "Plans", "Pending_Approval",
        "Approved", "Done", "Logs",
    ]
    for folder in expected:
        assert (tmp_path / folder).is_dir(), f"Missing folder: {folder}"


def test_setup_vault_creates_handbook(tmp_path):
    """setup_vault should create a Company_Handbook.md with default content."""
    from setup_vault import setup_vault
    setup_vault(tmp_path)
    handbook = tmp_path / "Company_Handbook.md"
    assert handbook.exists()
    content = handbook.read_text()
    assert "# Company Handbook" in content


def test_setup_vault_is_idempotent(tmp_path):
    """Running setup_vault twice should not error or duplicate content."""
    from setup_vault import setup_vault
    setup_vault(tmp_path)
    setup_vault(tmp_path)
    assert (tmp_path / "Needs_Action").is_dir()
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_setup_vault.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# setup_vault.py
"""One-time Obsidian vault initialization."""
from pathlib import Path

VAULT_FOLDERS = [
    "Needs_Action",
    "Plans",
    "Pending_Approval",
    "Approved",
    "Done",
    "Logs",
]

DEFAULT_HANDBOOK = """\
# Company Handbook

## About
This handbook contains rules and preferences that guide your Digital FTE's behavior.
Edit this file to customize how Claude processes your emails and tasks.

## Email Processing Rules
- Prioritize emails from known contacts
- Flag invoices and payment requests for approval
- Archive newsletters after summarizing
- Urgent keywords: "urgent", "asap", "deadline", "overdue"

## Approval Thresholds
- All email replies: require approval
- All payment-related actions: require approval
- Archiving/labeling: auto-approve

## Tone & Style
- Professional and concise in all drafted responses
- Match the sender's formality level
- Always acknowledge receipt of important items
"""


def setup_vault(vault_path: Path) -> None:
    """Create vault folder structure and default files."""
    vault_path.mkdir(parents=True, exist_ok=True)

    for folder in VAULT_FOLDERS:
        (vault_path / folder).mkdir(exist_ok=True)

    handbook = vault_path / "Company_Handbook.md"
    if not handbook.exists():
        handbook.write_text(DEFAULT_HANDBOOK)


if __name__ == "__main__":
    from src.config import load_config
    cfg = load_config()
    setup_vault(cfg.vault_path)
    print(f"Vault initialized at: {cfg.vault_path}")
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_setup_vault.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add tests/test_setup_vault.py setup_vault.py
git commit -m "feat: add vault initialization script with folder structure and handbook"
```

---

### Task 5: Base Watcher Abstract Class

**Files:**
- Create: `tests/watchers/test_base_watcher.py`
- Create: `src/watchers/base_watcher.py`

**Step 1: Write the failing test**

```python
# tests/watchers/test_base_watcher.py
import time
from pathlib import Path
from unittest.mock import patch

import pytest


def test_base_watcher_is_abstract():
    """BaseWatcher cannot be instantiated directly."""
    from src.watchers.base_watcher import BaseWatcher
    with pytest.raises(TypeError):
        BaseWatcher(vault_path=Path("."), check_interval=10)


def test_concrete_watcher_creates_action_files(tmp_path):
    """A concrete watcher should call check_for_updates and create_action_file."""
    from src.watchers.base_watcher import BaseWatcher

    class FakeWatcher(BaseWatcher):
        def check_for_updates(self):
            return [{"id": "1", "subject": "Test"}]

        def create_action_file(self, item):
            path = self.needs_action_dir / f"{item['id']}.md"
            path.write_text(f"# {item['subject']}")
            return path

    watcher = FakeWatcher(vault_path=tmp_path, check_interval=10)
    assert watcher.needs_action_dir == tmp_path / "Needs_Action"
    items = watcher.check_for_updates()
    assert len(items) == 1
    path = watcher.create_action_file(items[0])
    assert path.exists()


def test_run_single_cycle(tmp_path):
    """run_once should process all items from check_for_updates."""
    from src.watchers.base_watcher import BaseWatcher

    class FakeWatcher(BaseWatcher):
        def check_for_updates(self):
            return [{"id": "1"}, {"id": "2"}]

        def create_action_file(self, item):
            path = self.needs_action_dir / f"{item['id']}.md"
            path.write_text("test")
            return path

    watcher = FakeWatcher(vault_path=tmp_path, check_interval=10)
    watcher.needs_action_dir.mkdir(parents=True, exist_ok=True)
    count = watcher.run_once()
    assert count == 2
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/watchers/test_base_watcher.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/watchers/base_watcher.py
"""Abstract base class for all watchers."""
import logging
from abc import ABC, abstractmethod
from pathlib import Path

logger = logging.getLogger("digital_fte.watcher")


class BaseWatcher(ABC):
    """Base class for watchers that monitor external sources and create action files."""

    def __init__(self, vault_path: Path, check_interval: int = 60):
        self.vault_path = vault_path
        self.check_interval = check_interval
        self.needs_action_dir = vault_path / "Needs_Action"
        self.needs_action_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def check_for_updates(self) -> list:
        """Check the external source for new items. Returns list of items."""
        ...

    @abstractmethod
    def create_action_file(self, item) -> Path:
        """Create a markdown action file for the given item. Returns file path."""
        ...

    def run_once(self) -> int:
        """Run a single check cycle. Returns number of items processed."""
        items = self.check_for_updates()
        count = 0
        for item in items:
            try:
                self.create_action_file(item)
                count += 1
            except Exception as e:
                logger.error(f"Failed to create action file: {e}")
        return count
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/watchers/test_base_watcher.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add tests/watchers/test_base_watcher.py src/watchers/base_watcher.py
git commit -m "feat: add abstract BaseWatcher class with run_once cycle"
```

---

### Task 6: Gmail Watcher

**Files:**
- Create: `tests/watchers/test_gmail_watcher.py`
- Create: `src/watchers/gmail_watcher.py`

**Step 1: Write the failing test**

```python
# tests/watchers/test_gmail_watcher.py
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_gmail_service():
    """Create a mock Gmail API service."""
    service = MagicMock()
    return service


@pytest.fixture
def vault(tmp_path):
    (tmp_path / "Needs_Action").mkdir()
    (tmp_path / "Logs").mkdir()
    return tmp_path


def test_gmail_watcher_check_for_updates_returns_messages(vault, mock_gmail_service):
    """check_for_updates should return list of email dicts."""
    from src.watchers.gmail_watcher import GmailWatcher

    # Mock the messages().list() call
    mock_gmail_service.users().messages().list.return_value.execute.return_value = {
        "messages": [{"id": "msg_1", "threadId": "t1"}]
    }
    # Mock the messages().get() call
    mock_gmail_service.users().messages().get.return_value.execute.return_value = {
        "id": "msg_1",
        "payload": {
            "headers": [
                {"name": "From", "value": "sender@test.com"},
                {"name": "Subject", "value": "Test Email"},
                {"name": "Date", "value": "Mon, 16 Feb 2026 10:00:00 +0000"},
            ],
            "body": {"data": "SGVsbG8gV29ybGQ="},  # "Hello World" base64
        },
        "labelIds": ["INBOX", "UNREAD"],
    }

    watcher = GmailWatcher(
        vault_path=vault,
        gmail_service=mock_gmail_service,
        gmail_filter="is:unread",
    )
    messages = watcher.check_for_updates()
    assert len(messages) == 1
    assert messages[0]["id"] == "msg_1"
    assert messages[0]["from"] == "sender@test.com"
    assert messages[0]["subject"] == "Test Email"


def test_gmail_watcher_check_no_messages(vault, mock_gmail_service):
    """check_for_updates should return empty list when no messages."""
    from src.watchers.gmail_watcher import GmailWatcher

    mock_gmail_service.users().messages().list.return_value.execute.return_value = {}
    watcher = GmailWatcher(
        vault_path=vault,
        gmail_service=mock_gmail_service,
    )
    messages = watcher.check_for_updates()
    assert messages == []


def test_gmail_watcher_creates_action_file(vault, mock_gmail_service):
    """create_action_file should write a markdown file with YAML frontmatter."""
    from src.watchers.gmail_watcher import GmailWatcher

    watcher = GmailWatcher(
        vault_path=vault,
        gmail_service=mock_gmail_service,
    )
    item = {
        "id": "msg_123",
        "from": "bob@example.com",
        "subject": "Invoice #42",
        "date": "2026-02-16T10:30:00Z",
        "body": "Please find attached the invoice.",
        "labels": ["INBOX", "IMPORTANT"],
    }
    path = watcher.create_action_file(item)
    assert path.exists()
    content = path.read_text()
    assert "type: email" in content
    assert "from: bob@example.com" in content
    assert "Invoice #42" in content
    assert "Please find attached the invoice." in content


def test_gmail_watcher_marks_as_processed(vault, mock_gmail_service):
    """After creating action file, watcher should label the email as processed."""
    from src.watchers.gmail_watcher import GmailWatcher

    # Mock label creation (already exists)
    mock_gmail_service.users().labels().list.return_value.execute.return_value = {
        "labels": [{"id": "Label_123", "name": "Processed-by-FTE"}]
    }
    watcher = GmailWatcher(
        vault_path=vault,
        gmail_service=mock_gmail_service,
    )
    watcher.mark_as_processed("msg_123")
    mock_gmail_service.users().messages().modify.assert_called_once()
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/watchers/test_gmail_watcher.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/watchers/gmail_watcher.py
"""Gmail watcher — polls Gmail API for unread emails and creates action files."""
import base64
import logging
from datetime import datetime, timezone
from pathlib import Path

from src.utils import log_action, slugify
from src.watchers.base_watcher import BaseWatcher

logger = logging.getLogger("digital_fte.gmail_watcher")

PROCESSED_LABEL = "Processed-by-FTE"


class GmailWatcher(BaseWatcher):
    """Watches Gmail for unread emails and creates action files."""

    def __init__(
        self,
        vault_path: Path,
        gmail_service,
        gmail_filter: str = "is:unread",
        check_interval: int = 60,
    ):
        super().__init__(vault_path, check_interval)
        self.service = gmail_service
        self.gmail_filter = gmail_filter
        self._processed_label_id = None

    def check_for_updates(self) -> list:
        """Fetch unread emails from Gmail."""
        try:
            results = (
                self.service.users()
                .messages()
                .list(userId="me", q=self.gmail_filter, maxResults=10)
                .execute()
            )
        except Exception as e:
            logger.error(f"Gmail API error: {e}")
            return []

        raw_messages = results.get("messages", [])
        if not raw_messages:
            return []

        messages = []
        for msg_ref in raw_messages:
            try:
                msg = (
                    self.service.users()
                    .messages()
                    .get(userId="me", id=msg_ref["id"], format="full")
                    .execute()
                )
                messages.append(self._parse_message(msg))
            except Exception as e:
                logger.error(f"Failed to fetch message {msg_ref['id']}: {e}")

        return messages

    def create_action_file(self, item: dict) -> Path:
        """Create a markdown action file for an email."""
        slug = slugify(item["subject"])[:50] or "no-subject"
        filename = f"email-{slug}-{item['id'][:8]}.md"
        path = self.needs_action_dir / filename

        content = f"""---
type: email
from: {item['from']}
subject: {item['subject']}
date: {item['date']}
priority: normal
gmail_id: {item['id']}
---

# New Email: {item['subject']}

**From:** {item['from']}
**Date:** {item['date']}
**Labels:** {', '.join(item.get('labels', []))}

## Body
{item['body']}

## Suggested Actions
- [ ] Reply
- [ ] Forward
- [ ] Archive
"""
        path.write_text(content, encoding="utf-8")
        logger.info(f"Created action file: {path.name}")

        # Log the action
        log_action(
            logs_dir=self.vault_path / "Logs",
            actor="gmail_watcher",
            action="email_detected",
            source=item["id"],
            result=f"action_file_created:{filename}",
        )

        # Mark as processed in Gmail
        self.mark_as_processed(item["id"])

        return path

    def mark_as_processed(self, message_id: str) -> None:
        """Apply the 'Processed-by-FTE' label to a Gmail message."""
        label_id = self._get_or_create_label()
        if label_id:
            try:
                self.service.users().messages().modify(
                    userId="me",
                    id=message_id,
                    body={"addLabelIds": [label_id]},
                ).execute()
            except Exception as e:
                logger.error(f"Failed to label message {message_id}: {e}")

    def _get_or_create_label(self) -> str | None:
        """Get or create the 'Processed-by-FTE' Gmail label."""
        if self._processed_label_id:
            return self._processed_label_id

        try:
            labels = (
                self.service.users()
                .labels()
                .list(userId="me")
                .execute()
                .get("labels", [])
            )
            for label in labels:
                if label["name"] == PROCESSED_LABEL:
                    self._processed_label_id = label["id"]
                    return label["id"]

            # Create the label
            result = (
                self.service.users()
                .labels()
                .create(userId="me", body={"name": PROCESSED_LABEL})
                .execute()
            )
            self._processed_label_id = result["id"]
            return result["id"]
        except Exception as e:
            logger.error(f"Failed to get/create label: {e}")
            return None

    @staticmethod
    def _parse_message(msg: dict) -> dict:
        """Parse a Gmail API message into a simplified dict."""
        headers = {
            h["name"].lower(): h["value"]
            for h in msg.get("payload", {}).get("headers", [])
        }
        body = ""
        payload = msg.get("payload", {})
        if "body" in payload and payload["body"].get("data"):
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
        elif "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                    break

        return {
            "id": msg["id"],
            "from": headers.get("from", "unknown"),
            "subject": headers.get("subject", "(no subject)"),
            "date": headers.get("date", datetime.now(timezone.utc).isoformat()),
            "body": body,
            "labels": msg.get("labelIds", []),
        }
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/watchers/test_gmail_watcher.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
git add tests/watchers/test_gmail_watcher.py src/watchers/gmail_watcher.py
git commit -m "feat: add Gmail watcher with polling, action files, and label tracking"
```

---

### Task 7: Gmail Authentication Helper

**Files:**
- Create: `src/auth.py`
- Create: `credentials/` directory

**Step 1: Write the auth module**

```python
# src/auth.py
"""Gmail OAuth 2.0 authentication helper."""
import logging
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger("digital_fte.auth")

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def get_gmail_service(credentials_dir: Path):
    """Authenticate and return a Gmail API service instance.

    Expects:
      - credentials_dir/client_secret.json  (OAuth client ID downloaded from Google Cloud Console)
      - credentials_dir/token.json          (auto-created after first auth)
    """
    credentials_dir.mkdir(parents=True, exist_ok=True)
    token_path = credentials_dir / "token.json"
    client_secret_path = credentials_dir / "client_secret.json"

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired Gmail token...")
            creds.refresh(Request())
        else:
            if not client_secret_path.exists():
                raise FileNotFoundError(
                    f"Missing {client_secret_path}. Download your OAuth client "
                    f"secret from Google Cloud Console and save it there.\n"
                    f"Guide: https://developers.google.com/gmail/api/quickstart/python"
                )
            logger.info("Starting OAuth flow — a browser window will open...")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(client_secret_path), SCOPES
            )
            creds = flow.run_local_server(port=0)

        token_path.write_text(creds.to_json())
        logger.info(f"Token saved to {token_path}")

    return build("gmail", "v1", credentials=creds)
```

**Step 2: Commit**

```bash
git add src/auth.py
git commit -m "feat: add Gmail OAuth authentication helper"
```

---

### Task 8: Orchestrator

**Files:**
- Create: `tests/test_orchestrator.py`
- Create: `src/orchestrator.py`

**Step 1: Write the failing test**

```python
# tests/test_orchestrator.py
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture
def vault(tmp_path):
    """Create a vault with all required folders."""
    for folder in ["Needs_Action", "Plans", "Pending_Approval", "Approved", "Done", "Logs"]:
        (tmp_path / folder).mkdir()
    (tmp_path / "Company_Handbook.md").write_text("# Handbook\nApprove all emails.")
    return tmp_path


def test_orchestrator_detects_new_action_file(vault):
    """Orchestrator should find new files in Needs_Action."""
    from src.orchestrator import Orchestrator

    orch = Orchestrator(vault_path=vault)
    # Drop an action file
    action_file = vault / "Needs_Action" / "email-test-abc123.md"
    action_file.write_text("---\ntype: email\n---\n# Test Email")
    pending = orch.get_pending_actions()
    assert len(pending) == 1
    assert pending[0].name == "email-test-abc123.md"


def test_orchestrator_generates_plan(vault):
    """process_action should create a plan file in Plans/."""
    from src.orchestrator import Orchestrator

    orch = Orchestrator(vault_path=vault)
    action_file = vault / "Needs_Action" / "email-test-abc123.md"
    action_file.write_text("---\ntype: email\nfrom: bob@test.com\nsubject: Hello\n---\n# Test\n\n## Body\nHi there")

    with patch.object(orch, "_invoke_claude") as mock_claude:
        mock_claude.return_value = "## Analysis\nGeneral greeting.\n\n## Recommended Actions\n1. Reply with acknowledgment\n\n## Requires Approval\n- [ ] Send reply email"
        plan_path = orch.process_action(action_file)

    assert plan_path.exists()
    assert plan_path.parent.name == "Pending_Approval"
    content = plan_path.read_text()
    assert "Analysis" in content
    # Original action file should be gone from Needs_Action
    assert not action_file.exists()


def test_orchestrator_moves_approved_to_done(vault):
    """When a file appears in Approved/, execute should move it to Done/."""
    from src.orchestrator import Orchestrator

    orch = Orchestrator(vault_path=vault)
    approved_file = vault / "Approved" / "plan-test.md"
    approved_file.write_text("# Plan\nSend reply.")
    orch.execute_approved(approved_file)
    assert not approved_file.exists()
    assert (vault / "Done" / "plan-test.md").exists()
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_orchestrator.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/orchestrator.py
"""Orchestrator — processes action files using Claude and manages the approval pipeline."""
import logging
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from src.utils import log_action

logger = logging.getLogger("digital_fte.orchestrator")


class Orchestrator:
    """Processes action files from Needs_Action and routes through the approval pipeline."""

    def __init__(self, vault_path: Path, claude_model: str = "claude-sonnet-4-5-20250929"):
        self.vault_path = vault_path
        self.claude_model = claude_model
        self.needs_action = vault_path / "Needs_Action"
        self.plans = vault_path / "Plans"
        self.pending_approval = vault_path / "Pending_Approval"
        self.approved = vault_path / "Approved"
        self.done = vault_path / "Done"
        self.logs = vault_path / "Logs"
        self.handbook_path = vault_path / "Company_Handbook.md"

    def get_pending_actions(self) -> list[Path]:
        """Get all unprocessed action files."""
        return sorted(self.needs_action.glob("*.md"))

    def get_approved_actions(self) -> list[Path]:
        """Get all approved action files ready for execution."""
        return sorted(self.approved.glob("*.md"))

    def process_action(self, action_file: Path) -> Path:
        """Process an action file: invoke Claude, create plan, route to approval."""
        logger.info(f"Processing: {action_file.name}")
        action_content = action_file.read_text(encoding="utf-8")

        handbook = ""
        if self.handbook_path.exists():
            handbook = self.handbook_path.read_text(encoding="utf-8")

        # Invoke Claude for analysis
        claude_response = self._invoke_claude(action_content, handbook)

        # Create plan file
        now = datetime.now(timezone.utc).isoformat()
        plan_name = action_file.name.replace("email-", "plan-")
        plan_content = f"""---
source: {action_file.name}
created: {now}
status: pending_approval
---

# Plan: {action_file.stem}

{claude_response}
"""
        # Route to Pending_Approval (all email actions need approval in Bronze)
        plan_path = self.pending_approval / plan_name
        plan_path.write_text(plan_content, encoding="utf-8")

        # Remove original action file
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
        """Execute an approved action (Bronze: log it and move to Done)."""
        logger.info(f"Executing approved action: {approved_file.name}")

        # Bronze tier: just log and move to Done
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

    def _invoke_claude(self, action_content: str, handbook: str) -> str:
        """Invoke Claude Code to analyze an action and generate a plan."""
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

Respond with:
## Analysis
[Your analysis]

## Recommended Actions
[Numbered list]

## Requires Approval
[Checklist of items needing human approval]
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

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_orchestrator.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add tests/test_orchestrator.py src/orchestrator.py
git commit -m "feat: add orchestrator with Claude integration and approval pipeline"
```

---

### Task 9: Main Entry Point

**Files:**
- Create: `main.py`

**Step 1: Write the main entry point**

```python
# main.py
"""Digital FTE — Main entry point.

Starts the Gmail watcher and orchestrator loops.
"""
import logging
import time
import sys
from pathlib import Path

from src.config import load_config
from src.utils import setup_logging
from src.auth import get_gmail_service
from src.watchers.gmail_watcher import GmailWatcher
from src.orchestrator import Orchestrator
from setup_vault import setup_vault


def main():
    cfg = load_config()
    logger = setup_logging(cfg.log_level)

    # Initialize vault
    setup_vault(cfg.vault_path)
    logger.info(f"Vault ready at: {cfg.vault_path}")

    # Authenticate with Gmail
    credentials_dir = Path("credentials")
    try:
        gmail_service = get_gmail_service(credentials_dir)
        logger.info("Gmail authenticated successfully")
    except FileNotFoundError as e:
        logger.error(str(e))
        logger.error(
            "\n=== SETUP REQUIRED ===\n"
            "1. Go to https://console.cloud.google.com/\n"
            "2. Create a project and enable the Gmail API\n"
            "3. Create OAuth 2.0 credentials (Desktop app)\n"
            "4. Download the JSON and save as credentials/client_secret.json\n"
            "5. Run this script again\n"
        )
        sys.exit(1)

    # Create watcher and orchestrator
    watcher = GmailWatcher(
        vault_path=cfg.vault_path,
        gmail_service=gmail_service,
        gmail_filter=cfg.gmail_filter,
        check_interval=cfg.gmail_check_interval,
    )
    orchestrator = Orchestrator(
        vault_path=cfg.vault_path,
        claude_model=cfg.claude_model,
    )

    logger.info(
        f"Digital FTE started — watching Gmail every {cfg.gmail_check_interval}s "
        f"(filter: {cfg.gmail_filter})"
    )
    logger.info("Press Ctrl+C to stop")

    # Main loop
    try:
        while True:
            # 1. Check Gmail for new emails
            count = watcher.run_once()
            if count > 0:
                logger.info(f"Gmail: {count} new email(s) detected")

            # 2. Process any pending action files
            for action_file in orchestrator.get_pending_actions():
                orchestrator.process_action(action_file)

            # 3. Execute any approved actions
            for approved_file in orchestrator.get_approved_actions():
                orchestrator.execute_approved(approved_file)

            time.sleep(cfg.gmail_check_interval)
    except KeyboardInterrupt:
        logger.info("Digital FTE shutting down. Goodbye!")


if __name__ == "__main__":
    main()
```

**Step 2: Commit**

```bash
git add main.py
git commit -m "feat: add main entry point with watcher and orchestrator loop"
```

---

### Task 10: Gmail API Setup Guide in README

**Files:**
- Create: `README.md`

**Step 1: Write README with setup instructions**

Include:
1. Project overview (what Digital FTE is)
2. Architecture diagram (text-based)
3. Prerequisites (Python 3.13+, Claude Code, Obsidian)
4. Gmail API setup guide (step-by-step with screenshots links)
   - Create Google Cloud project
   - Enable Gmail API
   - Create OAuth credentials
   - Download client_secret.json
5. Installation steps (`pip install`, `.env` setup, vault init)
6. Running the system (`python main.py`)
7. How to use (check vault folders in Obsidian, approve/reject)
8. Security notes
9. Tier declaration: Bronze

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup guide and architecture overview"
```

---

### Task 11: Integration Test — End-to-End Flow

**Files:**
- Create: `tests/test_integration.py`

**Step 1: Write integration test**

```python
# tests/test_integration.py
"""End-to-end integration test using mocked Gmail service."""
from pathlib import Path
from unittest.mock import MagicMock, patch


def test_full_email_pipeline(tmp_path):
    """Test the full flow: watcher detects email → orchestrator processes → approval → done."""
    from setup_vault import setup_vault
    from src.watchers.gmail_watcher import GmailWatcher
    from src.orchestrator import Orchestrator

    # Setup vault
    setup_vault(tmp_path)

    # Mock Gmail service
    service = MagicMock()
    service.users().messages().list.return_value.execute.return_value = {
        "messages": [{"id": "msg_e2e", "threadId": "t1"}]
    }
    service.users().messages().get.return_value.execute.return_value = {
        "id": "msg_e2e",
        "payload": {
            "headers": [
                {"name": "From", "value": "client@example.com"},
                {"name": "Subject", "value": "Project Update"},
                {"name": "Date", "value": "2026-02-16"},
            ],
            "body": {"data": "UHJvamVjdCBpcyBvbiB0cmFjaw=="},
        },
        "labelIds": ["INBOX"],
    }
    service.users().labels().list.return_value.execute.return_value = {
        "labels": [{"id": "L1", "name": "Processed-by-FTE"}]
    }

    # Step 1: Watcher detects email
    watcher = GmailWatcher(vault_path=tmp_path, gmail_service=service)
    count = watcher.run_once()
    assert count == 1
    action_files = list((tmp_path / "Needs_Action").glob("*.md"))
    assert len(action_files) == 1

    # Step 2: Orchestrator processes action
    orch = Orchestrator(vault_path=tmp_path)
    with patch.object(orch, "_invoke_claude") as mock_claude:
        mock_claude.return_value = "## Analysis\nProject status update.\n\n## Recommended Actions\n1. Acknowledge receipt\n\n## Requires Approval\n- [ ] Send reply"
        plan_path = orch.process_action(action_files[0])

    assert plan_path.parent.name == "Pending_Approval"
    assert len(list((tmp_path / "Needs_Action").glob("*.md"))) == 0

    # Step 3: Simulate human approval (move file)
    import shutil
    approved_path = tmp_path / "Approved" / plan_path.name
    shutil.move(str(plan_path), str(approved_path))

    # Step 4: Orchestrator executes approved action
    done_path = orch.execute_approved(approved_path)
    assert done_path.parent.name == "Done"
    assert not approved_path.exists()
```

**Step 2: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: All tests pass

**Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add end-to-end integration test for full email pipeline"
```

---

## Summary

| Task | Description | Est. Time |
|------|-------------|-----------|
| 1 | Project scaffolding | 15 min |
| 2 | Configuration module | 20 min |
| 3 | Logging utilities | 20 min |
| 4 | Vault initialization | 20 min |
| 5 | Base watcher class | 15 min |
| 6 | Gmail watcher | 45 min |
| 7 | Gmail auth helper | 15 min |
| 8 | Orchestrator | 45 min |
| 9 | Main entry point | 15 min |
| 10 | README & docs | 30 min |
| 11 | Integration test | 20 min |
| **Total** | | **~4.5 hours** |
