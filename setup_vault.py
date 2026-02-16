"""One-time Obsidian vault initialization."""
from pathlib import Path

VAULT_FOLDERS = ["Needs_Action", "Plans", "Pending_Approval", "Approved", "Done", "Logs", "Incoming_Files"]

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
