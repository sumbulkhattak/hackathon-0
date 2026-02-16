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
