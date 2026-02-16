# Digital FTE Gold — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add self-review loops so the agent learns from rejected plans — analyzing what went wrong, storing learnings in Agent_Memory.md, and using that memory to improve future plans.

**Architecture:** Extend the existing Orchestrator with `review_rejected()` and `get_rejected_actions()` methods. Add `Rejected/` folder and `Agent_Memory.md` to the vault. Update `_invoke_claude()` to include agent memory in prompts. Wire the review step into the main loop.

**Tech Stack:** Python 3.13, google-api-python-client, pyyaml, pytest

---

### Task 1: Add Rejected/ folder and Agent_Memory.md to vault setup

**Files:**
- Modify: `tests/test_setup_vault.py`
- Modify: `setup_vault.py`

**Step 1: Write failing tests**

Add to `tests/test_setup_vault.py`:

```python
def test_setup_vault_creates_rejected_folder(tmp_path):
    """setup_vault should create a Rejected/ folder."""
    from setup_vault import setup_vault
    setup_vault(tmp_path)
    assert (tmp_path / "Rejected").is_dir()


def test_setup_vault_creates_agent_memory(tmp_path):
    """setup_vault should create Agent_Memory.md with starter template."""
    from setup_vault import setup_vault
    setup_vault(tmp_path)
    memory = tmp_path / "Agent_Memory.md"
    assert memory.exists()
    content = memory.read_text()
    assert "# Agent Memory" in content
    assert "## Patterns" in content


def test_setup_vault_does_not_overwrite_agent_memory(tmp_path):
    """setup_vault should not overwrite existing Agent_Memory.md."""
    from setup_vault import setup_vault
    memory = tmp_path / "Agent_Memory.md"
    memory.mkdir(parents=True, exist_ok=True) if not tmp_path.exists() else None
    tmp_path.mkdir(parents=True, exist_ok=True)
    memory.write_text("# Agent Memory\n\n## Patterns\n- Custom learning here\n")
    setup_vault(tmp_path)
    content = memory.read_text()
    assert "Custom learning here" in content
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_setup_vault.py -v`
Expected: FAIL — no Rejected/ folder, no Agent_Memory.md

**Step 3: Update setup_vault.py**

Add `"Rejected"` to `VAULT_FOLDERS`:

```python
VAULT_FOLDERS = ["Needs_Action", "Plans", "Pending_Approval", "Approved", "Done", "Logs", "Incoming_Files", "Rejected"]
```

Add `DEFAULT_AGENT_MEMORY` constant:

```python
DEFAULT_AGENT_MEMORY = """\
# Agent Memory

Learnings from past decisions. This file is read by Claude alongside the Company Handbook when generating plans.

## Patterns
<!-- New learnings are appended here automatically -->
"""
```

Add to `setup_vault()` after the handbook creation:

```python
    agent_memory = vault_path / "Agent_Memory.md"
    if not agent_memory.exists():
        agent_memory.write_text(DEFAULT_AGENT_MEMORY)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_setup_vault.py -v`
Expected: ALL PASS

Also update the existing `test_setup_vault_creates_all_folders` test to include "Rejected" in the expected list.

**Step 5: Run full suite**

Run: `pytest tests/ -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add tests/test_setup_vault.py setup_vault.py
git commit -m "feat: add Rejected/ folder and Agent_Memory.md to vault setup"
```

---

### Task 2: Add `get_rejected_actions()` to Orchestrator

**Files:**
- Modify: `tests/test_orchestrator.py`
- Modify: `src/orchestrator.py`

**Step 1: Update the vault fixture**

The existing `vault` fixture in `tests/test_orchestrator.py` doesn't include `Rejected/`. Update it:

Change line 9 from:
```python
    for folder in ["Needs_Action", "Plans", "Pending_Approval", "Approved", "Done", "Logs"]:
```
To:
```python
    for folder in ["Needs_Action", "Plans", "Pending_Approval", "Approved", "Done", "Logs", "Rejected"]:
```

**Step 2: Write failing test**

Add to `tests/test_orchestrator.py`:

```python
def test_orchestrator_detects_rejected_files(vault):
    """get_rejected_actions should find files in Rejected/ folder."""
    from src.orchestrator import Orchestrator
    orch = Orchestrator(vault_path=vault)
    rejected_file = vault / "Rejected" / "plan-bad.md"
    rejected_file.write_text("---\nstatus: pending_approval\n---\n\n# Plan\nBad plan.")
    rejected = orch.get_rejected_actions()
    assert len(rejected) == 1
    assert rejected[0].name == "plan-bad.md"
```

**Step 3: Run tests to verify it fails**

Run: `pytest tests/test_orchestrator.py::test_orchestrator_detects_rejected_files -v`
Expected: FAIL — `Orchestrator` has no `get_rejected_actions` method

**Step 4: Implement**

Add to `Orchestrator.__init__()` after `self.done = vault_path / "Done"`:

```python
        self.rejected = vault_path / "Rejected"
```

Add new method after `get_approved_actions()`:

```python
    def get_rejected_actions(self) -> list[Path]:
        return sorted(self.rejected.glob("*.md"))
```

**Step 5: Run tests**

Run: `pytest tests/test_orchestrator.py -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add tests/test_orchestrator.py src/orchestrator.py
git commit -m "feat: add get_rejected_actions to orchestrator"
```

---

### Task 3: Add `review_rejected()` method

**Files:**
- Modify: `tests/test_orchestrator.py`
- Modify: `src/orchestrator.py`

**Step 1: Write failing tests**

Add to `tests/test_orchestrator.py`:

```python
def make_rejected_plan(vault, name="plan-rejected-test.md"):
    """Helper: create a rejected plan file."""
    content = """---
source: email-test.md
created: 2026-02-16T10:00:00Z
status: pending_approval
action: reply
gmail_id: msg_rej1
to: bob@test.com
subject: "Re: Hello"
---

# Plan: email-test

## Analysis
General greeting.

## Reply Draft
---BEGIN REPLY---
Dear Sir/Madam,

I hereby acknowledge your correspondence.

Yours faithfully
---END REPLY---
"""
    path = vault / "Rejected" / name
    path.write_text(content)
    return path


def test_review_rejected_moves_to_done(vault):
    """review_rejected should move the file to Done/ after review."""
    from src.orchestrator import Orchestrator
    orch = Orchestrator(vault_path=vault)
    rejected = make_rejected_plan(vault)
    with patch.object(orch, "_invoke_claude_review") as mock_review:
        mock_review.return_value = "Don't use overly formal language. Match the sender's casual tone."
        orch.review_rejected(rejected)
    assert not rejected.exists()
    assert (vault / "Done" / "plan-rejected-test.md").exists()


def test_review_rejected_appends_learning_to_memory(vault):
    """review_rejected should append the learning to Agent_Memory.md."""
    from src.orchestrator import Orchestrator
    memory_path = vault / "Agent_Memory.md"
    memory_path.write_text("# Agent Memory\n\n## Patterns\n")
    orch = Orchestrator(vault_path=vault)
    rejected = make_rejected_plan(vault)
    with patch.object(orch, "_invoke_claude_review") as mock_review:
        mock_review.return_value = "Don't use overly formal language."
        orch.review_rejected(rejected)
    content = memory_path.read_text()
    assert "Don't use overly formal language." in content


def test_review_rejected_handles_claude_failure(vault):
    """review_rejected should still move to Done if Claude fails."""
    from src.orchestrator import Orchestrator
    orch = Orchestrator(vault_path=vault)
    rejected = make_rejected_plan(vault)
    with patch.object(orch, "_invoke_claude_review") as mock_review:
        mock_review.return_value = ""
        orch.review_rejected(rejected)
    assert not rejected.exists()
    assert (vault / "Done" / "plan-rejected-test.md").exists()


def test_review_rejected_creates_memory_if_missing(vault):
    """review_rejected should create Agent_Memory.md if it doesn't exist."""
    from src.orchestrator import Orchestrator
    orch = Orchestrator(vault_path=vault)
    rejected = make_rejected_plan(vault)
    # Ensure no memory file exists
    memory_path = vault / "Agent_Memory.md"
    assert not memory_path.exists()
    with patch.object(orch, "_invoke_claude_review") as mock_review:
        mock_review.return_value = "A useful learning."
        orch.review_rejected(rejected)
    assert memory_path.exists()
    content = memory_path.read_text()
    assert "A useful learning." in content
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_orchestrator.py -k "review_rejected" -v`
Expected: FAIL — no `review_rejected` method

**Step 3: Implement `review_rejected()` and `_invoke_claude_review()`**

Add `self.memory_path = vault_path / "Agent_Memory.md"` to `__init__()` after `self.handbook_path`.

Add new methods to the Orchestrator class:

```python
    def review_rejected(self, rejected_file: Path) -> Path:
        """Analyze a rejected plan, extract a learning, and update Agent Memory."""
        logger.info(f"Reviewing rejected plan: {rejected_file.name}")
        plan_content = rejected_file.read_text(encoding="utf-8")

        # Read current memory
        memory = ""
        if self.memory_path.exists():
            memory = self.memory_path.read_text(encoding="utf-8")

        # Ask Claude why this was rejected
        learning = self._invoke_claude_review(plan_content, memory)

        # Append learning to Agent_Memory.md
        if learning.strip():
            now = datetime.now(timezone.utc).isoformat()
            entry = f"\n- **{now}** — Rejected plan for \"{rejected_file.stem}\": {learning}\n"
            if not self.memory_path.exists():
                self.memory_path.write_text(
                    "# Agent Memory\n\n## Patterns\n" + entry
                )
            else:
                with open(self.memory_path, "a", encoding="utf-8") as f:
                    f.write(entry)
            logger.info(f"Learning added to Agent Memory: {learning[:80]}...")
        else:
            logger.warning(f"No learning extracted for {rejected_file.name}")

        # Move to Done
        dest = self.done / rejected_file.name
        shutil.move(str(rejected_file), str(dest))
        log_action(
            logs_dir=self.logs,
            actor="orchestrator",
            action="rejection_reviewed",
            source=rejected_file.name,
            result="learning_added" if learning.strip() else "no_learning",
        )
        logger.info(f"Rejected plan reviewed and moved to Done: {dest.name}")
        return dest

    def _invoke_claude_review(self, plan_content: str, memory: str) -> str:
        """Ask Claude to analyze a rejected plan and produce a learning."""
        prompt = f"""You are reviewing a rejected plan. The human moved this plan to Rejected/ instead of approving it. Analyze what went wrong and produce ONE concise learning (1-2 sentences) that should guide future plans.

## The Rejected Plan
{plan_content}

## Current Agent Memory
{memory}

Respond with ONLY the learning text, no markdown headers or formatting.
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
                logger.error(f"Claude review error: {result.stderr}")
                return ""
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.error(f"Claude review failed: {e}")
            return ""
```

**Step 4: Run tests**

Run: `pytest tests/test_orchestrator.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add tests/test_orchestrator.py src/orchestrator.py
git commit -m "feat: add review_rejected with learning extraction and memory append"
```

---

### Task 4: Update `_invoke_claude()` to include Agent Memory

**Files:**
- Modify: `tests/test_orchestrator.py`
- Modify: `src/orchestrator.py`

**Step 1: Write failing test**

Add to `tests/test_orchestrator.py`:

```python
def test_invoke_claude_includes_agent_memory(vault):
    """_invoke_claude should include Agent_Memory.md content in the prompt."""
    from src.orchestrator import Orchestrator
    memory_path = vault / "Agent_Memory.md"
    memory_path.write_text("# Agent Memory\n\n## Patterns\n- Don't be overly formal.\n")
    orch = Orchestrator(vault_path=vault)
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="## Analysis\nTest response.")
        orch._invoke_claude("Test action content", "Test handbook")
        call_args = mock_run.call_args[0][0]
        prompt = call_args[-1]  # Last arg is the prompt string
        assert "Agent Memory" in prompt
        assert "Don't be overly formal." in prompt
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_orchestrator.py::test_invoke_claude_includes_agent_memory -v`
Expected: FAIL — current prompt doesn't include Agent Memory

**Step 3: Update `_invoke_claude()`**

Change the method signature to read memory and include it in the prompt:

```python
    def _invoke_claude(self, action_content: str, handbook: str) -> str:
        # Read agent memory
        memory = ""
        if self.memory_path.exists():
            memory = self.memory_path.read_text(encoding="utf-8")

        memory_section = ""
        if memory.strip():
            memory_section = f"""
## Agent Memory (learnings from past decisions)
{memory}
"""

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

**Step 4: Run tests**

Run: `pytest tests/test_orchestrator.py -v`
Expected: ALL PASS

**Step 5: Run full suite**

Run: `pytest tests/ -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add tests/test_orchestrator.py src/orchestrator.py
git commit -m "feat: include Agent Memory in Claude plan generation prompt"
```

---

### Task 5: Wire review step into main loop

**Files:**
- Modify: `main.py`

**Step 1: Add the rejected-review step to the main loop**

After the existing approved-actions loop, add:

```python
            for rejected_file in orchestrator.get_rejected_actions():
                orchestrator.review_rejected(rejected_file)
```

The full loop block becomes:

```python
        while True:
            count = watcher.run_once()
            if count > 0:
                logger.info(f"Gmail: {count} new email(s) detected")
            if file_watcher:
                file_count = file_watcher.run_once()
                if file_count > 0:
                    logger.info(f"Files: {file_count} new file(s) detected")
            for action_file in orchestrator.get_pending_actions():
                orchestrator.process_action(action_file)
            for approved_file in orchestrator.get_approved_actions():
                orchestrator.execute_approved(approved_file)
            for rejected_file in orchestrator.get_rejected_actions():
                orchestrator.review_rejected(rejected_file)
            time.sleep(cfg.gmail_check_interval)
```

**Step 2: Run full suite**

Run: `pytest tests/ -v`
Expected: ALL PASS

**Step 3: Commit**

```bash
git add main.py
git commit -m "feat: wire rejection review loop into main entry point"
```

---

### Task 6: Add end-to-end integration test for rejection flow

**Files:**
- Modify: `tests/test_integration.py`

**Step 1: Write the integration test**

Add to `tests/test_integration.py`:

```python
def test_rejection_feedback_loop(tmp_path):
    """End-to-end: email → plan → reject → learning added to Agent Memory."""
    from setup_vault import setup_vault
    from src.watchers.gmail_watcher import GmailWatcher
    from src.orchestrator import Orchestrator

    setup_vault(tmp_path)

    service = MagicMock()
    service.users().messages().list.return_value.execute.return_value = {
        "messages": [{"id": "msg_rej_e2e", "threadId": "t_rej"}]
    }
    service.users().messages().get.return_value.execute.return_value = {
        "id": "msg_rej_e2e",
        "threadId": "t_rej",
        "payload": {
            "headers": [
                {"name": "From", "value": "vip@example.com"},
                {"name": "Subject", "value": "Urgent Request"},
                {"name": "Date", "value": "2026-02-16"},
            ],
            "body": {"data": "SSBuZWVkIHRoaXMgZG9uZSBBU0FQ"},
        },
        "labelIds": ["INBOX"],
    }
    service.users().labels().list.return_value.execute.return_value = {
        "labels": [{"id": "L1", "name": "Processed-by-FTE"}]
    }

    # Step 1: Watcher detects email
    watcher = GmailWatcher(vault_path=tmp_path, gmail_service=service)
    watcher.run_once()
    action_files = list((tmp_path / "Needs_Action").glob("*.md"))
    assert len(action_files) == 1

    # Step 2: Orchestrator creates plan with a reply
    orch = Orchestrator(vault_path=tmp_path, gmail_service=service)
    claude_plan = (
        "## Analysis\nUrgent request from VIP.\n\n"
        "## Recommended Actions\n1. Reply immediately\n\n"
        "## Requires Approval\n- [ ] Send reply\n\n"
        "## Reply Draft\n"
        "---BEGIN REPLY---\n"
        "Dear Sir/Madam,\n\nI have received your request and will process it.\n\n"
        "Yours faithfully\n"
        "---END REPLY---"
    )
    with patch.object(orch, "_invoke_claude") as mock_claude:
        mock_claude.return_value = claude_plan
        plan_path = orch.process_action(action_files[0])

    assert plan_path.parent.name == "Pending_Approval"

    # Step 3: Human rejects the plan (too formal)
    rejected_path = tmp_path / "Rejected" / plan_path.name
    shutil.move(str(plan_path), str(rejected_path))

    # Step 4: Orchestrator reviews rejection and learns
    with patch.object(orch, "_invoke_claude_review") as mock_review:
        mock_review.return_value = "Don't use 'Dear Sir/Madam' or 'Yours faithfully'. Match the sender's informal tone."
        done_path = orch.review_rejected(rejected_path)

    assert done_path.parent.name == "Done"
    assert not rejected_path.exists()

    # Step 5: Verify learning was added to Agent Memory
    memory_content = (tmp_path / "Agent_Memory.md").read_text()
    assert "Don't use 'Dear Sir/Madam'" in memory_content
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
git commit -m "test: add end-to-end integration test for rejection feedback loop"
```

---

### Task 7: Update README for Gold tier

**Files:**
- Modify: `README.md`

**Step 1: Update README**

1. Change title from `# Digital FTE — Silver Tier` to `# Digital FTE — Gold Tier`

2. Update tagline:
   > Your life and business on autopilot. Local-first, agent-driven, human-in-the-loop. Now with self-improving plans.

3. Update architecture diagram to show the rejection feedback loop:
   ```
   Gmail ──► Gmail Watcher ──► vault/Needs_Action/
                                       │
                               Orchestrator + Claude ◄── vault/Agent_Memory.md
                                       │
                               vault/Pending_Approval/
                                       │
                                 Human reviews
                                    │      │
                            Approved/   Rejected/
                                │          │
                          Gmail Reply   Claude reviews
                                │          │
                            Done/    learning → Agent_Memory.md
                                          │
                                        Done/
   ```

4. Update layer 3:
   > 3. **Action** — Approved plans are executed; rejected plans generate learnings

5. Add to the agent behavior list:
   > 7. **Learn from rejections** — analyze rejected plans and store learnings in Agent Memory

6. Add `Agent_Memory.md` and `Rejected/` to vault structure section

7. Update tier declaration:
   > **Gold Tier** — Gmail watcher with reply sending, file watcher, self-review loops that learn from rejected plans, Obsidian vault with approval pipeline.

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update README for Gold tier with self-review loops"
```

---

### Task 8: Final verification

**Step 1: Run the full test suite**

Run: `pytest tests/ -v`
Expected: ALL PASS

**Step 2: Verify imports**

Run: `python -c "from src.orchestrator import Orchestrator; print('All imports OK')"`
Expected: `All imports OK`

**Step 3: Verify vault setup**

Run: `python -c "from setup_vault import setup_vault; from pathlib import Path; import tempfile; p = Path(tempfile.mkdtemp()); setup_vault(p); assert (p / 'Rejected').is_dir(); assert (p / 'Agent_Memory.md').exists(); print('Vault setup OK')"`
Expected: `Vault setup OK`

**Step 4: Commit**

```bash
git add -A
git commit -m "feat: Digital FTE Gold tier — self-review loops with rejection learning"
```
