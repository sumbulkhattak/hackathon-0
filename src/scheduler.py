"""Scheduler — run Digital FTE tasks on a schedule.

Supports two modes:
1. Built-in scheduler (uses APScheduler for interval/cron-like scheduling)
2. External scheduling (cron/Task Scheduler docs for one-shot runs)

Usage:
    # Run as scheduled service
    python -m src.scheduler

    # One-shot run (for cron/Task Scheduler)
    python -m src.scheduler --once
"""
import logging
import time
import sys
from pathlib import Path

logger = logging.getLogger("digital_fte.scheduler")


def run_once(vault_path: Path, gmail_service=None, claude_model: str = "claude-sonnet-4-5-20250929",
             daily_send_limit: int = 20, auto_approve_threshold: float = 1.0,
             vip_senders: list[str] | None = None, file_watch_enabled: bool = False,
             file_watch_dry_run: bool = False) -> dict:
    """Execute one full cycle of the Digital FTE pipeline.

    Returns a dict with counts of actions taken.
    """
    from src.watchers.gmail_watcher import GmailWatcher
    from src.watchers.file_watcher import FileWatcher
    from src.orchestrator import Orchestrator
    from src.dashboard import update_dashboard

    results = {
        "emails_detected": 0,
        "files_detected": 0,
        "actions_processed": 0,
        "approved_executed": 0,
        "rejections_reviewed": 0,
    }

    # Gmail watcher
    if gmail_service:
        watcher = GmailWatcher(
            vault_path=vault_path,
            gmail_service=gmail_service,
            vip_senders=vip_senders or [],
        )
        results["emails_detected"] = watcher.run_once()

    # File watcher
    if file_watch_enabled:
        file_watcher = FileWatcher(
            vault_path=vault_path,
            dry_run=file_watch_dry_run,
            claude_model=claude_model,
        )
        results["files_detected"] = file_watcher.run_once()

    # Orchestrator
    orchestrator = Orchestrator(
        vault_path=vault_path,
        claude_model=claude_model,
        gmail_service=gmail_service,
        daily_send_limit=daily_send_limit,
        auto_approve_threshold=auto_approve_threshold,
    )

    for action_file in orchestrator.get_pending_actions():
        orchestrator.process_action(action_file)
        results["actions_processed"] += 1

    for approved_file in orchestrator.get_approved_actions():
        orchestrator.execute_approved(approved_file)
        results["approved_executed"] += 1

    for rejected_file in orchestrator.get_rejected_actions():
        orchestrator.review_rejected(rejected_file)
        results["rejections_reviewed"] += 1

    # Update dashboard
    update_dashboard(vault_path)

    return results


def generate_cron_entry(python_path: str = "python", project_dir: str = ".") -> str:
    """Generate a crontab entry for scheduling the Digital FTE.

    Returns a cron line that runs every 5 minutes.
    """
    return f"*/5 * * * * cd {project_dir} && {python_path} -m src.scheduler --once >> /tmp/digital-fte.log 2>&1"


def generate_task_scheduler_xml(python_path: str = "python", project_dir: str = ".") -> str:
    """Generate Windows Task Scheduler XML for scheduling the Digital FTE."""
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <TimeTrigger>
      <Repetition>
        <Interval>PT5M</Interval>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
      <StartBoundary>2026-01-01T00:00:00</StartBoundary>
      <Enabled>true</Enabled>
    </TimeTrigger>
  </Triggers>
  <Actions>
    <Exec>
      <Command>{python_path}</Command>
      <Arguments>-m src.scheduler --once</Arguments>
      <WorkingDirectory>{project_dir}</WorkingDirectory>
    </Exec>
  </Actions>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT10M</ExecutionTimeLimit>
  </Settings>
</Task>"""


if __name__ == "__main__":
    from src.config import load_config
    from src.utils import setup_logging
    from src.auth import get_gmail_service
    from setup_vault import setup_vault

    cfg = load_config()
    log = setup_logging(cfg.log_level)
    setup_vault(cfg.vault_path)

    once_mode = "--once" in sys.argv

    try:
        gmail_service = get_gmail_service(Path("credentials"))
    except FileNotFoundError:
        logger.warning("Gmail credentials not found. Running without Gmail.")
        gmail_service = None

    if once_mode:
        logger.info("Running one-shot cycle...")
        results = run_once(
            vault_path=cfg.vault_path,
            gmail_service=gmail_service,
            claude_model=cfg.claude_model,
            daily_send_limit=cfg.daily_send_limit,
            auto_approve_threshold=cfg.auto_approve_threshold,
            vip_senders=cfg.vip_senders,
            file_watch_enabled=cfg.file_watch_enabled,
            file_watch_dry_run=cfg.file_watch_dry_run,
        )
        logger.info(f"Cycle complete: {results}")
    else:
        logger.info(f"Starting scheduler (interval: {cfg.gmail_check_interval}s)")
        logger.info("Press Ctrl+C to stop")
        try:
            while True:
                results = run_once(
                    vault_path=cfg.vault_path,
                    gmail_service=gmail_service,
                    claude_model=cfg.claude_model,
                    daily_send_limit=cfg.daily_send_limit,
                    auto_approve_threshold=cfg.auto_approve_threshold,
                    vip_senders=cfg.vip_senders,
                    file_watch_enabled=cfg.file_watch_enabled,
                    file_watch_dry_run=cfg.file_watch_dry_run,
                )
                total = sum(results.values())
                if total > 0:
                    logger.info(f"Cycle: {results}")
                time.sleep(cfg.gmail_check_interval)
        except KeyboardInterrupt:
            logger.info("Scheduler stopped.")
