"""Retry logic with exponential backoff and graceful degradation."""
import time
import shutil
import logging
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

logger = logging.getLogger("digital_fte.retry")


class TransientError(Exception):
    """Errors that may resolve on retry (network, API rate limit, timeout)."""
    pass


class PermanentError(Exception):
    """Errors that won't resolve on retry (auth revoked, bad data)."""
    pass


def with_retry(max_attempts=3, base_delay=1, max_delay=60, on_failure=None):
    """Decorator for exponential backoff retry on TransientError.

    Args:
        max_attempts: Maximum retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay cap in seconds
        on_failure: Optional callback(func_name, error, attempt) on each failure
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except PermanentError:
                    raise
                except TransientError as e:
                    last_error = e
                    if on_failure is not None:
                        on_failure(func.__name__, e, attempt)
                    if attempt < max_attempts:
                        delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                        logger.warning(
                            "Attempt %d/%d for %s failed: %s. Retrying in %.1fs...",
                            attempt, max_attempts, func.__name__, e, delay,
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            "All %d attempts for %s exhausted. Last error: %s",
                            max_attempts, func.__name__, e,
                        )
            raise last_error
        return wrapper
    return decorator


def queue_failed_action(vault_path, action_file, error_msg):
    """Move a failed action to a quarantine queue for later retry.

    Creates vault/Quarantine/ folder if needed.
    Writes error metadata to the file's frontmatter.

    Args:
        vault_path: Path to the vault root
        action_file: Path to the action file that failed
        error_msg: Description of the failure
    """
    vault_path = Path(vault_path)
    action_file = Path(action_file)

    quarantine_dir = vault_path / "Quarantine"
    quarantine_dir.mkdir(parents=True, exist_ok=True)

    # Read original content
    content = action_file.read_text(encoding="utf-8")
    now = datetime.now(timezone.utc).isoformat()

    # Inject quarantine metadata into frontmatter
    if content.startswith("---"):
        # Find the closing ---
        end_idx = content.index("---", 3)
        frontmatter = content[3:end_idx].strip()
        body = content[end_idx + 3:]
        new_frontmatter = (
            f"{frontmatter}\n"
            f"quarantine_error: {error_msg}\n"
            f"quarantine_time: {now}"
        )
        new_content = f"---\n{new_frontmatter}\n---{body}"
    else:
        # No frontmatter — add one
        new_content = (
            f"---\n"
            f"quarantine_error: {error_msg}\n"
            f"quarantine_time: {now}\n"
            f"---\n{content}"
        )

    dest = quarantine_dir / action_file.name
    dest.write_text(new_content, encoding="utf-8")
    action_file.unlink()
    logger.info("Quarantined %s: %s", action_file.name, error_msg)


def process_quarantine(vault_path, min_age_seconds=300):
    """Check quarantined items and move recoverable ones back to Needs_Action/.

    Items older than min_age_seconds are assumed to be past the transient
    failure window and are moved back for reprocessing.

    Args:
        vault_path: Path to the vault root
        min_age_seconds: Minimum age in seconds before an item is eligible
            to be moved back (default: 300 = 5 minutes)

    Returns:
        List of Path objects that were moved back to Needs_Action/.
    """
    vault_path = Path(vault_path)
    quarantine_dir = vault_path / "Quarantine"
    needs_action = vault_path / "Needs_Action"

    if not quarantine_dir.exists():
        return []

    moved = []
    now = datetime.now(timezone.utc)

    for item in sorted(quarantine_dir.glob("*.md")):
        content = item.read_text(encoding="utf-8")

        # Parse quarantine_time from frontmatter
        quarantine_time = _extract_quarantine_time(content)
        if quarantine_time is None:
            # No timestamp — treat as old enough to retry
            pass
        else:
            age = (now - quarantine_time).total_seconds()
            if age < min_age_seconds:
                logger.debug("Skipping %s (age=%.0fs < %ds)", item.name, age, min_age_seconds)
                continue

        # Strip quarantine metadata and move back
        clean_content = _strip_quarantine_metadata(content)
        dest = needs_action / item.name
        dest.write_text(clean_content, encoding="utf-8")
        item.unlink()
        moved.append(dest)
        logger.info("Restored %s from quarantine to Needs_Action/", item.name)

    return moved


def _extract_quarantine_time(content):
    """Extract quarantine_time from file frontmatter as a datetime."""
    for line in content.splitlines():
        if line.strip().startswith("quarantine_time:"):
            time_str = line.split(":", 1)[1].strip()
            try:
                return datetime.fromisoformat(time_str)
            except ValueError:
                return None
    return None


def _strip_quarantine_metadata(content):
    """Remove quarantine_error and quarantine_time lines from frontmatter."""
    if not content.startswith("---"):
        return content

    end_idx = content.index("---", 3)
    frontmatter_lines = content[3:end_idx].strip().splitlines()
    body = content[end_idx + 3:]

    cleaned_lines = [
        line for line in frontmatter_lines
        if not line.strip().startswith("quarantine_error:")
        and not line.strip().startswith("quarantine_time:")
    ]

    cleaned_fm = "\n".join(cleaned_lines)
    return f"---\n{cleaned_fm}\n---{body}"
