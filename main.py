"""Digital FTE — Main entry point."""
import logging
import time
import sys
from pathlib import Path

from src.config import load_config
from src.utils import setup_logging
from src.auth import get_gmail_service
from src.watchers.gmail_watcher import GmailWatcher
from src.watchers.file_watcher import FileWatcher
from src.orchestrator import Orchestrator
from setup_vault import setup_vault


def main():
    cfg = load_config()
    logger = setup_logging(cfg.log_level)
    setup_vault(cfg.vault_path)
    logger.info(f"Vault ready at: {cfg.vault_path}")
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
    watcher = GmailWatcher(
        vault_path=cfg.vault_path,
        gmail_service=gmail_service,
        gmail_filter=cfg.gmail_filter,
        check_interval=cfg.gmail_check_interval,
        vip_senders=cfg.vip_senders,
    )
    orchestrator = Orchestrator(
        vault_path=cfg.vault_path,
        claude_model=cfg.claude_model,
        gmail_service=gmail_service,
        daily_send_limit=cfg.daily_send_limit,
        auto_approve_threshold=cfg.auto_approve_threshold,
    )
    if cfg.auto_approve_threshold < 1.0:
        logger.info(f"Auto-approve enabled (threshold: {cfg.auto_approve_threshold})")
    else:
        logger.info("Auto-approve disabled (threshold: 1.0)")
    file_watcher = None
    if cfg.file_watch_enabled:
        file_watcher = FileWatcher(
            vault_path=cfg.vault_path,
            dry_run=cfg.file_watch_dry_run,
            claude_model=cfg.claude_model,
        )
        mode = "dry-run" if cfg.file_watch_dry_run else "live"
        logger.info(f"File watcher enabled ({mode})")

    logger.info(
        f"Digital FTE started — watching Gmail every {cfg.gmail_check_interval}s "
        f"(filter: {cfg.gmail_filter}, send_limit: {cfg.daily_send_limit}/day)"
    )
    logger.info("Press Ctrl+C to stop")
    try:
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
    except KeyboardInterrupt:
        logger.info("Digital FTE shutting down. Goodbye!")


if __name__ == "__main__":
    main()
