"""Orchestrator — processes action files using Claude and manages the approval pipeline."""
import logging
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from src.utils import log_action

logger = logging.getLogger("digital_fte.orchestrator")


class Orchestrator:
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
        return sorted(self.needs_action.glob("*.md"))

    def get_approved_actions(self) -> list[Path]:
        return sorted(self.approved.glob("*.md"))

    def process_action(self, action_file: Path) -> Path:
        logger.info(f"Processing: {action_file.name}")
        action_content = action_file.read_text(encoding="utf-8")
        handbook = ""
        if self.handbook_path.exists():
            handbook = self.handbook_path.read_text(encoding="utf-8")
        claude_response = self._invoke_claude(action_content, handbook)
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
