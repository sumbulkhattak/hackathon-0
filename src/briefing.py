"""CEO Briefing generator -- weekly business audit and summary.

Generates a "Monday Morning CEO Briefing" by analyzing:
- Completed tasks from vault/Done/ (this week)
- Pending items in vault/Needs_Action/ and vault/Pending_Approval/
- Activity logs from vault/Logs/
- Quarantined items (errors/failures)

Output: Markdown briefing saved to vault/Briefings/YYYY-MM-DD_Monday_Briefing.md
"""
import json
import logging
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger("digital_fte.briefing")

# Action types mapped to stat keys
ACTION_MAP = {
    "email_sent": "emails_sent",
    "plan_created": "plans_created",
    "auto_approved": "auto_approved",
    "executed": "manually_approved",
    "rejection_reviewed": "rejected",
    "send_failed": "errors",
    "reply_failed": "errors",
    "quarantined": "errors",
}


def get_period_stats(vault_path: Path, period_days: int = 7) -> dict:
    """Collect statistics from logs for the given period.

    Returns dict with:
    - emails_sent: int
    - plans_created: int
    - auto_approved: int
    - manually_approved: int
    - rejected: int
    - errors: int
    - total_actions: int
    """
    stats = {
        "emails_sent": 0,
        "plans_created": 0,
        "auto_approved": 0,
        "manually_approved": 0,
        "rejected": 0,
        "errors": 0,
        "total_actions": 0,
    }

    logs_dir = vault_path / "Logs"
    if not logs_dir.exists():
        return stats

    cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)

    for log_file in sorted(logs_dir.glob("*.json")):
        # Parse the date from the filename (YYYY-MM-DD.json)
        try:
            file_date_str = log_file.stem  # e.g. "2026-02-17"
            file_date = datetime.strptime(file_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue

        # Skip log files outside the period
        if file_date < cutoff:
            continue

        try:
            entries = json.loads(log_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        for entry in entries:
            action = entry.get("action", "")
            stats["total_actions"] += 1
            stat_key = ACTION_MAP.get(action)
            if stat_key:
                stats[stat_key] += 1

    return stats


def get_completed_items(vault_path: Path, period_days: int = 7) -> list[str]:
    """Return names of files in Done/ modified within the period."""
    done_dir = vault_path / "Done"
    if not done_dir.exists():
        return []

    cutoff_time = time.time() - (period_days * 86400)
    items = []

    for f in sorted(done_dir.iterdir()):
        if f.is_file() and f.stat().st_mtime >= cutoff_time:
            items.append(f.name)

    return items


def get_bottlenecks(vault_path: Path) -> list[dict]:
    """Return items that have been pending for too long (> 24 hours in Pending_Approval).

    Returns list of {name, folder, age_hours}.
    """
    bottlenecks = []
    threshold_seconds = 24 * 3600  # 24 hours
    now = time.time()

    for folder_name in ["Pending_Approval", "Needs_Action"]:
        folder = vault_path / folder_name
        if not folder.exists():
            continue
        for f in sorted(folder.iterdir()):
            if not f.is_file():
                continue
            age_seconds = now - f.stat().st_mtime
            if age_seconds > threshold_seconds:
                bottlenecks.append({
                    "name": f.name,
                    "folder": folder_name,
                    "age_hours": int(age_seconds / 3600),
                })

    return bottlenecks


def generate_briefing(vault_path: Path, period_days: int = 7) -> str:
    """Generate a CEO briefing markdown covering the last N days.

    Analyzes:
    - Done/ folder: completed items this period
    - Needs_Action/ + Pending_Approval/: pending bottlenecks
    - Logs/: activity counts (emails sent, plans created, approvals, rejections)
    - Quarantine/: error items

    Returns markdown string.
    """
    now = datetime.now(timezone.utc)
    period_start = now - timedelta(days=period_days)

    stats = get_period_stats(vault_path, period_days)
    completed = get_completed_items(vault_path, period_days)
    bottlenecks = get_bottlenecks(vault_path)

    # Count pending items
    needs_action_count = _count_files(vault_path / "Needs_Action")
    pending_approval_count = _count_files(vault_path / "Pending_Approval")
    quarantine_count = _count_files(vault_path / "Quarantine")

    # Executive summary
    total = stats["total_actions"]
    if total == 0:
        summary = "No activity recorded this period. The system is idle."
    else:
        summary = (
            f"This period saw {total} total actions: "
            f"{stats['emails_sent']} emails processed, "
            f"{stats['plans_created']} plans created, "
            f"and {stats['errors']} errors."
        )

    # Build completed tasks section
    if completed:
        completed_lines = "\n".join(f"- [x] {name}" for name in completed)
    else:
        completed_lines = "No tasks completed this period."

    # Build bottlenecks section
    if bottlenecks:
        bottleneck_rows = "\n".join(
            f"| {b['name']} | {b['folder']} | {b['age_hours']} hours |"
            for b in bottlenecks
        )
        bottleneck_table = (
            "| Item | Folder | Waiting |\n"
            "|------|--------|---------|"
            f"\n{bottleneck_rows}"
        )
    else:
        bottleneck_table = "No bottlenecks detected."

    # Build proactive suggestions
    suggestions = []
    if bottlenecks:
        suggestions.append("- Review items in Pending_Approval that have been waiting > 24 hours")
    if quarantine_count > 0:
        suggestions.append(f"- {quarantine_count} quarantined item(s) need attention")
    if stats["errors"] > 0:
        suggestions.append(f"- {stats['errors']} error(s) occurred this period; review Logs for details")
    if not suggestions:
        suggestions.append("- No immediate actions required")
    suggestions_text = "\n".join(suggestions)

    briefing = f"""---
generated: {now.strftime("%Y-%m-%dT%H:%M:%SZ")}
period: {period_start.strftime("%Y-%m-%d")} to {now.strftime("%Y-%m-%d")}
---

# Monday Morning CEO Briefing

## Executive Summary
{summary}

## Activity This Period
| Metric | Count |
|--------|-------|
| Emails processed | {stats['emails_sent']} |
| Plans created | {stats['plans_created']} |
| Auto-approved | {stats['auto_approved']} |
| Manually approved | {stats['manually_approved']} |
| Rejected | {stats['rejected']} |
| Errors | {stats['errors']} |

## Completed Tasks
{completed_lines}

## Bottlenecks
{bottleneck_table}

## Pending Items
- Needs_Action: {needs_action_count} items
- Pending_Approval: {pending_approval_count} items
- Quarantine: {quarantine_count} items

## Proactive Suggestions
{suggestions_text}

---
*Generated by Digital FTE — Monday Morning CEO Briefing*
"""
    return briefing


def save_briefing(vault_path: Path, content: str) -> Path:
    """Save briefing to vault/Briefings/YYYY-MM-DD_Briefing.md and return the path."""
    briefings_dir = vault_path / "Briefings"
    briefings_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = briefings_dir / f"{today}_Briefing.md"
    path.write_text(content, encoding="utf-8")
    logger.info(f"Briefing saved to {path}")
    return path


def _count_files(folder: Path) -> int:
    """Count files in a folder, returning 0 if folder doesn't exist."""
    if not folder.exists():
        return 0
    return sum(1 for f in folder.iterdir() if f.is_file())
