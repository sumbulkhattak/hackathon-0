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
    daily_send_limit: int
    file_watch_enabled: bool
    file_watch_dry_run: bool
    auto_approve_threshold: float
    vip_senders: list[str]
    web_enabled: bool
    web_port: int


def load_config() -> Config:
    """Load configuration from environment variables with defaults."""
    load_dotenv()
    return Config(
        vault_path=Path(os.getenv("VAULT_PATH", "./vault")).resolve(),
        gmail_check_interval=int(os.getenv("GMAIL_CHECK_INTERVAL", "60")),
        gmail_filter=os.getenv("GMAIL_FILTER", "is:unread"),
        claude_model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5-20250929"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        daily_send_limit=int(os.getenv("DAILY_SEND_LIMIT", "20")),
        file_watch_enabled=os.getenv("FILE_WATCH_ENABLED", "false").lower() == "true",
        file_watch_dry_run=os.getenv("FILE_WATCH_DRY_RUN", "false").lower() == "true",
        auto_approve_threshold=float(os.getenv("AUTO_APPROVE_THRESHOLD", "1.0")),
        vip_senders=[s.strip() for s in os.getenv("VIP_SENDERS", "").split(",") if s.strip()],
        web_enabled=os.getenv("WEB_ENABLED", "true").lower() == "true",
        web_port=int(os.getenv("WEB_PORT", "8000")),
    )
