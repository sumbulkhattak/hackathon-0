# Digital FTE Platinum — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add confidence-based auto-approve so high-confidence plans execute without human review, controlled by a configurable threshold (disabled by default).

**Architecture:** Update Claude's prompt to include a `## Confidence` section in its response. Add `extract_confidence()` utility to parse the score. Extend `process_action()` to route high-confidence plans directly to Approved/ and call `execute_approved()` immediately. Add `AUTO_APPROVE_THRESHOLD` config (default 1.0 = disabled). Log auto-approved actions distinctly for audit.

**Tech Stack:** Python 3.13, google-api-python-client, pyyaml, pytest

---

### Task 1: Add `extract_confidence()` utility function

**Files:**
- Modify: `tests/test_utils.py`
- Modify: `src/utils.py`

**Step 1: Write failing tests**

Add to `tests/test_utils.py`:

```python
def test_extract_confidence_parses_valid_score():
    """extract_confidence should parse a float from ## Confidence section."""
    from src.utils import extract_confidence
    response = "## Analysis\nSome analysis.\n\n## Confidence\n0.85\n\n## Recommended Actions\n1. Reply"
    assert extract_confidence(response) == 0.85


def test_extract_confidence_returns_zero_when_missing():
    """extract_confidence should return 0.0 when ## Confidence section is absent."""
    from src.utils import extract_confidence
    response = "## Analysis\nSome analysis.\n\n## Recommended Actions\n1. Reply"
    assert extract_confidence(response) == 0.0


def test_extract_confidence_returns_zero_for_invalid_value():
    """extract_confidence should return 0.0 when confidence value is not a number."""
    from src.utils import extract_confidence
    response = "## Analysis\nSome analysis.\n\n## Confidence\nhigh\n\n## Recommended Actions\n1. Reply"
    assert extract_confidence(response) == 0.0
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_utils.py -k "extract_confidence" -v`
Expected: FAIL — `extract_confidence` not found

**Step 3: Implement `extract_confidence()`**

Add to `src/utils.py` after the `extract_reply_block` function:

```python
def extract_confidence(response: str) -> float:
    """Extract confidence score from Claude's ## Confidence section.

    Returns 0.0 if the section is missing or the value is not a valid float.
    """
    marker = "## Confidence"
    idx = response.find(marker)
    if idx == -1:
        return 0.0
    after = response[idx + len(marker):]
    # Take the first non-empty line after the header
    for line in after.split("\n"):
        line = line.strip()
        if line:
            try:
                return float(line)
            except ValueError:
                return 0.0
    return 0.0
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_utils.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add tests/test_utils.py src/utils.py
git commit -m "feat: add extract_confidence utility for parsing Claude confidence scores"
```

---

### Task 2: Add `auto_approve_threshold` to Config

**Files:**
- Modify: `tests/test_config.py`
- Modify: `src/config.py`
- Modify: `.env.example`

**Step 1: Write failing tests**

Add to `tests/test_config.py`:

```python
def test_config_loads_auto_approve_threshold(monkeypatch):
    """Config should read AUTO_APPROVE_THRESHOLD from environment."""
    monkeypatch.setenv("AUTO_APPROVE_THRESHOLD", "0.85")
    from src.config import load_config
    cfg = load_config()
    assert cfg.auto_approve_threshold == 0.85


def test_config_auto_approve_threshold_default(monkeypatch):
    """Config should default auto_approve_threshold to 1.0 (disabled)."""
    monkeypatch.delenv("AUTO_APPROVE_THRESHOLD", raising=False)
    from src.config import load_config
    cfg = load_config()
    assert cfg.auto_approve_threshold == 1.0
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config.py -k "auto_approve" -v`
Expected: FAIL — `Config` has no `auto_approve_threshold` field

**Step 3: Update `src/config.py`**

Add `auto_approve_threshold: float` field to the `Config` dataclass after `file_watch_dry_run`:

```python
    auto_approve_threshold: float
```

Add to `load_config()` return statement after `file_watch_dry_run`:

```python
        auto_approve_threshold=float(os.getenv("AUTO_APPROVE_THRESHOLD", "1.0")),
```

**Step 4: Update `.env.example`**

Add at the end of `.env.example`:

```
# Auto-approve threshold (0.0-1.0). Plans with confidence >= threshold
# skip human review and execute immediately. Default 1.0 = disabled.
AUTO_APPROVE_THRESHOLD=1.0
```

**Step 5: Run tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add tests/test_config.py src/config.py .env.example
git commit -m "feat: add auto_approve_threshold config (default 1.0 = disabled)"
```

---

### Task 3: Update Claude prompt to request confidence score

**Files:**
- Modify: `tests/test_orchestrator.py`
- Modify: `src/orchestrator.py`

**Step 1: Write failing test**

Add to `tests/test_orchestrator.py`:

```python
def test_invoke_claude_prompt_requests_confidence(vault):
    """_invoke_claude prompt should ask Claude for a ## Confidence section."""
    from src.orchestrator import Orchestrator
    orch = Orchestrator(vault_path=vault)
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="## Analysis\nTest.")
        orch._invoke_claude("Test action", "Test handbook")
        call_args = mock_run.call_args[0][0]
        prompt = call_args[-1]
        assert "## Confidence" in prompt
        assert "0.0 to 1.0" in prompt
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_orchestrator.py::test_invoke_claude_prompt_requests_confidence -v`
Expected: FAIL — current prompt doesn't mention Confidence

**Step 3: Update `_invoke_claude()` prompt in `src/orchestrator.py`**

In the `_invoke_claude()` method, update the prompt string. Add instruction 7 to the `## Instructions` block:

```
7. Rate your confidence that this plan requires no human edits (0.0 to 1.0)
```

Add `## Confidence` to the response format after the Reply Draft section:

```
## Confidence
[0.0 to 1.0 — how confident you are this plan needs no human edits]
```

The full updated response format section becomes:

```python
        prompt = f"""You are a Digital FTE (AI employee). Analyze the following action item and create a plan.

## Company Handbook
{handbook}
{memory_section}
## Action Item
{action_content}

## Instructions
1. Analyze the action item
2. Determine what needs to be done
3. List recommended actions
4. Identify which actions require human approval
5. If a reply email is appropriate, draft the full reply text
6. Apply any relevant learnings from Agent Memory
7. Rate your confidence that this plan requires no human edits (0.0 to 1.0)

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

## Confidence
[0.0 to 1.0 — how confident you are this plan needs no human edits]
"""
```

**Step 4: Run tests**

Run: `pytest tests/test_orchestrator.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add tests/test_orchestrator.py src/orchestrator.py
git commit -m "feat: update Claude prompt to request confidence score"
```

---

### Task 4: Add `auto_approve_threshold` to Orchestrator constructor

**Files:**
- Modify: `tests/test_orchestrator.py`
- Modify: `src/orchestrator.py`

**Step 1: Write failing test**

Add to `tests/test_orchestrator.py`:

```python
def test_orchestrator_stores_auto_approve_threshold(vault):
    """Orchestrator should accept and store auto_approve_threshold."""
    from src.orchestrator import Orchestrator
    orch = Orchestrator(vault_path=vault, auto_approve_threshold=0.85)
    assert orch.auto_approve_threshold == 0.85


def test_orchestrator_auto_approve_threshold_default(vault):
    """Orchestrator should default auto_approve_threshold to 1.0."""
    from src.orchestrator import Orchestrator
    orch = Orchestrator(vault_path=vault)
    assert orch.auto_approve_threshold == 1.0
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_orchestrator.py -k "auto_approve_threshold" -v`
Expected: FAIL — `Orchestrator.__init__` has no `auto_approve_threshold` parameter

**Step 3: Update Orchestrator `__init__`**

In `src/orchestrator.py`, update the `__init__` signature to add `auto_approve_threshold`:

Change:
```python
    def __init__(self, vault_path: Path, claude_model: str = "claude-sonnet-4-5-20250929",
                 gmail_service=None, daily_send_limit: int = 20):
```

To:
```python
    def __init__(self, vault_path: Path, claude_model: str = "claude-sonnet-4-5-20250929",
                 gmail_service=None, daily_send_limit: int = 20,
                 auto_approve_threshold: float = 1.0):
```

Add inside `__init__` after `self.daily_send_limit = daily_send_limit`:

```python
        self.auto_approve_threshold = auto_approve_threshold
```

**Step 4: Run tests**

Run: `pytest tests/test_orchestrator.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add tests/test_orchestrator.py src/orchestrator.py
git commit -m "feat: add auto_approve_threshold to Orchestrator constructor"
```

---

### Task 5: Implement auto-approve routing in `process_action()`

**Files:**
- Modify: `tests/test_orchestrator.py`
- Modify: `src/orchestrator.py`

**Step 1: Write failing tests**

Add to `tests/test_orchestrator.py`:

```python
def test_process_action_auto_approves_high_confidence(vault):
    """process_action should auto-approve and execute when confidence >= threshold."""
    from src.orchestrator import Orchestrator
    mock_gmail = MagicMock()
    mock_gmail.users().messages().get.return_value.execute.return_value = {
        "id": "msg_auto1", "threadId": "t1",
        "payload": {"headers": [{"name": "Message-ID", "value": "<orig@test.com>"}]},
    }
    mock_gmail.users().messages().send.return_value.execute.return_value = {
        "id": "sent_auto1", "threadId": "t1",
    }
    orch = Orchestrator(
        vault_path=vault, gmail_service=mock_gmail,
        auto_approve_threshold=0.8,
    )
    action_file = vault / "Needs_Action" / "email-auto-test.md"
    action_file.write_text(
        "---\ntype: email\nfrom: bob@test.com\nsubject: Hello\ngmail_id: msg_auto1\n---\n# Test\n\n## Body\nHi there"
    )
    claude_response = (
        "## Analysis\nSimple greeting.\n\n"
        "## Recommended Actions\n1. Reply with acknowledgment\n\n"
        "## Requires Approval\n- [ ] Send reply\n\n"
        "## Reply Draft\n"
        "---BEGIN REPLY---\nHi Bob,\n\nThanks for reaching out!\n\nBest\n---END REPLY---\n\n"
        "## Confidence\n0.92"
    )
    with patch.object(orch, "_invoke_claude") as mock_claude:
        mock_claude.return_value = claude_response
        result_path = orch.process_action(action_file)
    # Should end up in Done/, not Pending_Approval/
    assert result_path.parent.name == "Done"
    assert not action_file.exists()
    assert len(list((vault / "Pending_Approval").glob("*.md"))) == 0
    mock_gmail.users().messages().send.assert_called_once()


def test_process_action_routes_to_pending_below_threshold(vault):
    """process_action should route to Pending_Approval when confidence < threshold."""
    from src.orchestrator import Orchestrator
    orch = Orchestrator(vault_path=vault, auto_approve_threshold=0.9)
    action_file = vault / "Needs_Action" / "email-low-conf.md"
    action_file.write_text(
        "---\ntype: email\nfrom: bob@test.com\nsubject: Hello\n---\n# Test\n\n## Body\nHi"
    )
    claude_response = (
        "## Analysis\nNeeds review.\n\n"
        "## Recommended Actions\n1. Reply\n\n"
        "## Requires Approval\n- [ ] Send reply\n\n"
        "## Confidence\n0.65"
    )
    with patch.object(orch, "_invoke_claude") as mock_claude:
        mock_claude.return_value = claude_response
        result_path = orch.process_action(action_file)
    assert result_path.parent.name == "Pending_Approval"


def test_auto_approve_disabled_by_default(vault):
    """Default threshold 1.0 should never auto-approve (nothing scores > 1.0)."""
    from src.orchestrator import Orchestrator
    orch = Orchestrator(vault_path=vault)
    action_file = vault / "Needs_Action" / "email-default.md"
    action_file.write_text(
        "---\ntype: email\nfrom: bob@test.com\nsubject: Hi\n---\n# Test"
    )
    claude_response = (
        "## Analysis\nSimple.\n\n"
        "## Confidence\n0.99"
    )
    with patch.object(orch, "_invoke_claude") as mock_claude:
        mock_claude.return_value = claude_response
        result_path = orch.process_action(action_file)
    # threshold=1.0, confidence=0.99 → still goes to Pending_Approval
    assert result_path.parent.name == "Pending_Approval"


def test_auto_approve_respects_send_limit(vault):
    """Auto-approve should route to Pending_Approval when daily send limit is hit."""
    from src.orchestrator import Orchestrator
    mock_gmail = MagicMock()
    orch = Orchestrator(
        vault_path=vault, gmail_service=mock_gmail,
        daily_send_limit=0, auto_approve_threshold=0.5,
    )
    action_file = vault / "Needs_Action" / "email-limit.md"
    action_file.write_text(
        "---\ntype: email\nfrom: bob@test.com\nsubject: Hi\ngmail_id: msg1\n---\n# Test"
    )
    claude_response = (
        "## Analysis\nSimple.\n\n"
        "## Reply Draft\n---BEGIN REPLY---\nHi\n---END REPLY---\n\n"
        "## Confidence\n0.95"
    )
    with patch.object(orch, "_invoke_claude") as mock_claude:
        mock_claude.return_value = claude_response
        result_path = orch.process_action(action_file)
    # Send limit hit → falls back to Pending_Approval
    assert result_path.parent.name == "Pending_Approval"
    mock_gmail.users().messages().send.assert_not_called()


def test_auto_approve_logs_action(vault):
    """Auto-approve should log with action 'auto_approved' and include confidence."""
    import json
    from datetime import datetime, timezone
    from src.orchestrator import Orchestrator
    mock_gmail = MagicMock()
    mock_gmail.users().messages().get.return_value.execute.return_value = {
        "id": "msg_log1", "threadId": "t1",
        "payload": {"headers": [{"name": "Message-ID", "value": "<x@test.com>"}]},
    }
    mock_gmail.users().messages().send.return_value.execute.return_value = {
        "id": "sent_log1", "threadId": "t1",
    }
    orch = Orchestrator(
        vault_path=vault, gmail_service=mock_gmail,
        auto_approve_threshold=0.8,
    )
    action_file = vault / "Needs_Action" / "email-log-test.md"
    action_file.write_text(
        "---\ntype: email\nfrom: alice@test.com\nsubject: Test\ngmail_id: msg_log1\n---\n# Test"
    )
    claude_response = (
        "## Analysis\nSimple.\n\n"
        "## Reply Draft\n---BEGIN REPLY---\nHi\n---END REPLY---\n\n"
        "## Confidence\n0.90"
    )
    with patch.object(orch, "_invoke_claude") as mock_claude:
        mock_claude.return_value = claude_response
        orch.process_action(action_file)
    # Check logs for auto_approved entry
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = vault / "Logs" / f"{today}.json"
    assert log_file.exists()
    entries = json.loads(log_file.read_text())
    auto_entries = [e for e in entries if e["action"] == "auto_approved"]
    assert len(auto_entries) >= 1
    assert "confidence:0.9" in auto_entries[0]["result"]
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_orchestrator.py -k "auto_approve" -v`
Expected: FAIL — process_action doesn't do auto-approve routing

**Step 3: Implement auto-approve routing in `process_action()`**

In `src/orchestrator.py`, add the import at the top of the file:

```python
from src.utils import log_action, parse_frontmatter, extract_reply_block, extract_confidence
```

Then update `process_action()`. After the plan is written to `pending_approval`, add the auto-approve check. The updated method becomes:

```python
    def process_action(self, action_file: Path) -> Path:
        logger.info(f"Processing: {action_file.name}")
        action_content = action_file.read_text(encoding="utf-8")
        handbook = ""
        if self.handbook_path.exists():
            handbook = self.handbook_path.read_text(encoding="utf-8")

        # Extract email metadata for reply context
        metadata = parse_frontmatter(action_file)
        claude_response = self._invoke_claude(action_content, handbook)

        # Parse confidence score
        confidence = extract_confidence(claude_response)

        now = datetime.now(timezone.utc).isoformat()
        plan_name = action_file.name.replace("email-", "plan-")

        # Build frontmatter — include reply fields if Claude generated a reply
        fm_lines = [
            f"source: {action_file.name}",
            f"created: {now}",
            "status: pending_approval",
            f"confidence: {confidence}",
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
        # Check if auto-approve is possible
        can_auto_approve = confidence >= self.auto_approve_threshold

        if can_auto_approve and "---BEGIN REPLY---" in claude_response:
            # Reply action — check send limit before auto-approving
            if not check_send_limit(self.logs, self.daily_send_limit):
                can_auto_approve = False

        if can_auto_approve:
            # Auto-approve: write to Approved/, execute, move to Done/
            approved_path = self.approved / plan_name
            approved_path.write_text(plan_content, encoding="utf-8")
            action_file.unlink()
            log_action(
                logs_dir=self.logs,
                actor="orchestrator",
                action="auto_approved",
                source=action_file.name,
                result=f"confidence:{confidence}",
            )
            logger.info(f"Auto-approved (confidence={confidence}): {plan_name}")
            return self.execute_approved(approved_path)
        else:
            # Normal flow: write to Pending_Approval/
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
```

Also add the `check_send_limit` import if not already present. Update the import line at the top of the file:

```python
from src.gmail_sender import send_reply, check_send_limit, increment_send_count
```

(This import already exists — no change needed.)

**Step 4: Run tests**

Run: `pytest tests/test_orchestrator.py -v`
Expected: ALL PASS

**Step 5: Run full suite**

Run: `pytest tests/ -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add tests/test_orchestrator.py src/orchestrator.py
git commit -m "feat: implement auto-approve routing in process_action"
```

---

### Task 6: Handle failed auto-approve send (fallback to Pending_Approval)

**Files:**
- Modify: `tests/test_orchestrator.py`
- Modify: `src/orchestrator.py`

**Step 1: Write failing test**

Add to `tests/test_orchestrator.py`:

```python
def test_auto_approve_failed_send_falls_back(vault):
    """Auto-approve should move plan to Pending_Approval if send fails."""
    from src.orchestrator import Orchestrator
    mock_gmail = MagicMock()
    mock_gmail.users().messages().get.return_value.execute.return_value = {
        "id": "msg_fail1", "threadId": "t1",
        "payload": {"headers": [{"name": "Message-ID", "value": "<x@test.com>"}]},
    }
    mock_gmail.users().messages().send.return_value.execute.side_effect = Exception("API error")
    orch = Orchestrator(
        vault_path=vault, gmail_service=mock_gmail,
        auto_approve_threshold=0.5,
    )
    action_file = vault / "Needs_Action" / "email-fail-test.md"
    action_file.write_text(
        "---\ntype: email\nfrom: bob@test.com\nsubject: Hi\ngmail_id: msg_fail1\n---\n# Test"
    )
    claude_response = (
        "## Analysis\nSimple.\n\n"
        "## Reply Draft\n---BEGIN REPLY---\nHi\n---END REPLY---\n\n"
        "## Confidence\n0.95"
    )
    with patch.object(orch, "_invoke_claude") as mock_claude:
        mock_claude.return_value = claude_response
        result_path = orch.process_action(action_file)
    # Failed send → plan should be in Pending_Approval for human review
    assert result_path.parent.name == "Pending_Approval"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_orchestrator.py::test_auto_approve_failed_send_falls_back -v`
Expected: FAIL — currently auto-approve doesn't handle send failures with fallback

**Step 3: Update `process_action()` auto-approve block**

Update the auto-approve block in `process_action()` to catch send failures and fall back to Pending_Approval/. Replace the auto-approve `if can_auto_approve:` block with:

```python
        if can_auto_approve:
            # Auto-approve: write to Approved/, execute, move to Done/
            approved_path = self.approved / plan_name
            approved_path.write_text(plan_content, encoding="utf-8")
            action_file.unlink()
            log_action(
                logs_dir=self.logs,
                actor="orchestrator",
                action="auto_approved",
                source=action_file.name,
                result=f"confidence:{confidence}",
            )
            logger.info(f"Auto-approved (confidence={confidence}): {plan_name}")
            result = self.execute_approved(approved_path)
            # If execute_approved returned a file still in Approved/, send failed
            if result.parent == self.approved:
                # Move to Pending_Approval for human review
                fallback_path = self.pending_approval / plan_name
                shutil.move(str(result), str(fallback_path))
                log_action(
                    logs_dir=self.logs,
                    actor="orchestrator",
                    action="auto_approve_fallback",
                    source=plan_name,
                    result="send_failed_moved_to_pending",
                )
                logger.warning(f"Auto-approve send failed, moved to Pending_Approval: {plan_name}")
                return fallback_path
            return result
```

**Step 4: Run tests**

Run: `pytest tests/test_orchestrator.py -v`
Expected: ALL PASS

**Step 5: Run full suite**

Run: `pytest tests/ -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add tests/test_orchestrator.py src/orchestrator.py
git commit -m "feat: add fallback to Pending_Approval when auto-approve send fails"
```

---

### Task 7: Wire `auto_approve_threshold` into main.py

**Files:**
- Modify: `main.py`

**Step 1: Update `main.py`**

In `main.py`, update the `Orchestrator` constructor call to pass `auto_approve_threshold` from config. Change:

```python
    orchestrator = Orchestrator(
        vault_path=cfg.vault_path,
        claude_model=cfg.claude_model,
        gmail_service=gmail_service,
        daily_send_limit=cfg.daily_send_limit,
    )
```

To:

```python
    orchestrator = Orchestrator(
        vault_path=cfg.vault_path,
        claude_model=cfg.claude_model,
        gmail_service=gmail_service,
        daily_send_limit=cfg.daily_send_limit,
        auto_approve_threshold=cfg.auto_approve_threshold,
    )
```

Also add a log line after the orchestrator is created to show the auto-approve status. Add after the orchestrator creation:

```python
    if cfg.auto_approve_threshold < 1.0:
        logger.info(f"Auto-approve enabled (threshold: {cfg.auto_approve_threshold})")
    else:
        logger.info("Auto-approve disabled (threshold: 1.0)")
```

**Step 2: Run full suite**

Run: `pytest tests/ -v`
Expected: ALL PASS

**Step 3: Commit**

```bash
git add main.py
git commit -m "feat: wire auto_approve_threshold into main entry point"
```

---

### Task 8: Add E2e integration test for auto-approve flow

**Files:**
- Modify: `tests/test_integration.py`

**Step 1: Write the integration test**

Add to `tests/test_integration.py`:

```python
def test_auto_approve_pipeline(tmp_path):
    """End-to-end: email -> plan -> auto-approve (high confidence) -> reply sent -> Done."""
    from setup_vault import setup_vault
    from src.watchers.gmail_watcher import GmailWatcher
    from src.orchestrator import Orchestrator

    setup_vault(tmp_path)

    service = MagicMock()
    service.users().messages().list.return_value.execute.return_value = {
        "messages": [{"id": "msg_auto_e2e", "threadId": "t_auto"}]
    }
    service.users().messages().get.return_value.execute.return_value = {
        "id": "msg_auto_e2e",
        "threadId": "t_auto",
        "payload": {
            "headers": [
                {"name": "From", "value": "colleague@example.com"},
                {"name": "Subject", "value": "Quick Question"},
                {"name": "Date", "value": "2026-02-16"},
                {"name": "Message-ID", "value": "<q1@example.com>"},
            ],
            "body": {"data": "V2hhdCB0aW1lIGlzIHRoZSBtZWV0aW5nPw=="},
        },
        "labelIds": ["INBOX"],
    }
    service.users().labels().list.return_value.execute.return_value = {
        "labels": [{"id": "L1", "name": "Processed-by-FTE"}]
    }
    service.users().messages().send.return_value.execute.return_value = {
        "id": "sent_auto_e2e", "threadId": "t_auto",
    }

    # Step 1: Watcher detects email
    watcher = GmailWatcher(vault_path=tmp_path, gmail_service=service)
    count = watcher.run_once()
    assert count == 1
    action_files = list((tmp_path / "Needs_Action").glob("*.md"))
    assert len(action_files) == 1

    # Step 2: Orchestrator processes with high confidence — auto-approves
    orch = Orchestrator(
        vault_path=tmp_path, gmail_service=service,
        daily_send_limit=20, auto_approve_threshold=0.8,
    )
    claude_response = (
        "## Analysis\nSimple question about meeting time.\n\n"
        "## Recommended Actions\n1. Reply with meeting time\n\n"
        "## Requires Approval\n- [ ] Send reply\n\n"
        "## Reply Draft\n"
        "---BEGIN REPLY---\n"
        "Hi,\n\nThe meeting is at 3pm.\n\nBest\n"
        "---END REPLY---\n\n"
        "## Confidence\n0.95"
    )
    with patch.object(orch, "_invoke_claude") as mock_claude:
        mock_claude.return_value = claude_response
        result_path = orch.process_action(action_files[0])

    # Should go directly to Done/ (no human review needed)
    assert result_path.parent.name == "Done"
    assert len(list((tmp_path / "Pending_Approval").glob("*.md"))) == 0
    assert len(list((tmp_path / "Approved").glob("*.md"))) == 0
    service.users().messages().send.assert_called_once()

    # Verify auto_approved log entry exists
    import json
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = tmp_path / "Logs" / f"{today}.json"
    entries = json.loads(log_file.read_text())
    auto_entries = [e for e in entries if e["action"] == "auto_approved"]
    assert len(auto_entries) >= 1
```

**Step 2: Run the test**

Run: `pytest tests/test_integration.py -v`
Expected: ALL PASS

**Step 3: Run full suite**

Run: `pytest tests/ -v`
Expected: ALL PASS

**Step 4: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add end-to-end integration test for auto-approve pipeline"
```

---

### Task 9: Update README for Platinum tier

**Files:**
- Modify: `README.md`

**Step 1: Update README**

1. Change title from `# Digital FTE — Gold Tier` to `# Digital FTE — Platinum Tier`

2. Update tagline:
   > Your life and business on autopilot. Local-first, agent-driven, human-in-the-loop. Now with confidence-based auto-approve.

3. Update architecture diagram to show auto-approve path:
   ```
   Gmail ──► Gmail Watcher ──► vault/Needs_Action/
                                       │
                               Orchestrator + Claude ◄── vault/Agent_Memory.md
                                       │
                               confidence >= threshold?
                                  │           │
                                 YES          NO
                                  │           │
                             Auto-execute   vault/Pending_Approval/
                                  │           │
                                  │      Human reviews
                                  │        │      │
                                  │  Approved/  Rejected/
                                  │      │          │
                                  │  Gmail Reply  Claude reviews
                                  │      │          │
                                Done/  Done/   learning → Agent_Memory.md
                                                    │
                                                  Done/
   ```

4. Update layer 3 to:
   > 3. **Action** — High-confidence plans auto-execute; others require approval; rejected plans generate learnings

5. Add to the configuration table:
   > | `AUTO_APPROVE_THRESHOLD` | `1.0` | Confidence threshold for auto-approve (1.0 = disabled) |

6. Update tier declaration:
   > **Platinum Tier** — Gmail watcher with reply sending, file watcher, self-review loops, confidence-based auto-approve for high-confidence plans, Obsidian vault with approval pipeline.

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update README for Platinum tier with auto-approve"
```

---

### Task 10: Final verification

**Step 1: Run the full test suite**

Run: `pytest tests/ -v`
Expected: ALL PASS

**Step 2: Verify imports**

Run: `python -c "from src.orchestrator import Orchestrator; from src.utils import extract_confidence; from src.config import load_config; print('All imports OK')"`
Expected: `All imports OK`

**Step 3: Verify config**

Run: `python -c "import os; os.environ['AUTO_APPROVE_THRESHOLD']='0.85'; from src.config import load_config; cfg = load_config(); assert cfg.auto_approve_threshold == 0.85; print('Config OK')"`
Expected: `Config OK`
