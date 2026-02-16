"""Gmail reply sender — builds and sends threaded email replies."""
import base64
import json
import logging
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path

logger = logging.getLogger("digital_fte.gmail_sender")


def send_reply(gmail_service, gmail_id: str, to: str, subject: str, body: str) -> dict:
    """Send a reply to an existing email thread.

    Fetches the original message to get threadId and Message-ID,
    builds a MIME message with proper threading headers, and sends it.
    """
    # Fetch original message for threading info
    original = gmail_service.users().messages().get(
        userId="me", id=gmail_id, format="metadata",
        metadataHeaders=["Message-ID"],
    ).execute()

    thread_id = original["threadId"]
    headers = {h["name"]: h["value"] for h in original.get("payload", {}).get("headers", [])}
    message_id = headers.get("Message-ID", "")

    # Build MIME message
    mime = MIMEText(body)
    mime["To"] = to
    mime["Subject"] = subject
    if message_id:
        mime["In-Reply-To"] = message_id
        mime["References"] = message_id

    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode("utf-8")

    result = gmail_service.users().messages().send(
        userId="me",
        body={"raw": raw, "threadId": thread_id},
    ).execute()

    logger.info(f"Reply sent to {to} (message_id={result['id']}, thread={thread_id})")
    return result


def check_send_limit(logs_dir: Path, limit: int) -> bool:
    """Return True if under the daily send limit, False if at/over."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    count_file = logs_dir / f".send_count_{today}.json"
    if not count_file.exists():
        return True
    data = json.loads(count_file.read_text())
    return data.get("count", 0) < limit


def increment_send_count(logs_dir: Path) -> int:
    """Increment the daily send counter. Returns new count."""
    logs_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    count_file = logs_dir / f".send_count_{today}.json"
    count = 0
    if count_file.exists():
        data = json.loads(count_file.read_text())
        count = data.get("count", 0)
    count += 1
    count_file.write_text(json.dumps({"count": count}))
    return count
