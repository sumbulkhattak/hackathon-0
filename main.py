"""Digital FTE — Main entry point."""
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
    try:
        while True:
            count = watcher.run_once()
            if count > 0:
                logger.info(f"Gmail: {count} new email(s) detected")
            for action_file in orchestrator.get_pending_actions():
                orchestrator.process_action(action_file)
            for approved_file in orchestrator.get_approved_actions():
                orchestrator.execute_approved(approved_file)
            time.sleep(cfg.gmail_check_interval)
    except KeyboardInterrupt:
        logger.info("Digital FTE shutting down. Goodbye!")


if __name__ == "__main__":
    main()
