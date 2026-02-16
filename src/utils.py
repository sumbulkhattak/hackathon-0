import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure and return the application logger."""
    logger = logging.getLogger("digital_fte")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def log_action(
    logs_dir: Path,
    actor: str,
    action: str,
    source: str,
    result: str,
) -> None:
    """Append a structured log entry to the daily JSON log file."""
    logs_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = logs_dir / f"{today}.json"

    entries = []
    if log_file.exists():
        entries = json.loads(log_file.read_text())

    entries.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "action": action,
        "source": source,
        "result": result,
    })
    log_file.write_text(json.dumps(entries, indent=2))


def slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def parse_frontmatter(file_path: Path) -> dict:
    """Extract YAML frontmatter from a markdown file."""
    text = file_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    try:
        return yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return {}


def extract_reply_block(file_path: Path) -> str | None:
    """Extract reply text between ---BEGIN REPLY--- and ---END REPLY--- markers."""
    text = file_path.read_text(encoding="utf-8")
    begin = "---BEGIN REPLY---"
    end = "---END REPLY---"
    start_idx = text.find(begin)
    end_idx = text.find(end)
    if start_idx == -1 or end_idx == -1:
        return None
    return text[start_idx + len(begin):end_idx].strip()
