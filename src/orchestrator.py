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
        claude_response = self._invoke_claude(action_content, handbook)

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
