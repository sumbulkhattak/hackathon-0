"""Gmail watcher — polls Gmail API for unread emails and creates action files."""
import base64
import logging
from datetime import datetime, timezone
from pathlib import Path

from src.utils import log_action, slugify
from src.watchers.base_watcher import BaseWatcher

logger = logging.getLogger("digital_fte.gmail_watcher")
PROCESSED_LABEL = "Processed-by-FTE"


class GmailWatcher(BaseWatcher):
    def __init__(self, vault_path: Path, gmail_service, gmail_filter: str = "is:unread", check_interval: int = 60):
        super().__init__(vault_path, check_interval)
        self.service = gmail_service
        self.gmail_filter = gmail_filter
        self._processed_label_id = None

    def check_for_updates(self) -> list:
        try:
            results = self.service.users().messages().list(userId="me", q=self.gmail_filter, maxResults=10).execute()
        except Exception as e:
            logger.error(f"Gmail API error: {e}")
            return []
        raw_messages = results.get("messages", [])
        if not raw_messages:
            return []
        messages = []
        for msg_ref in raw_messages:
            try:
                msg = self.service.users().messages().get(userId="me", id=msg_ref["id"], format="full").execute()
                messages.append(self._parse_message(msg))
            except Exception as e:
                logger.error(f"Failed to fetch message {msg_ref['id']}: {e}")
        return messages

    def create_action_file(self, item: dict) -> Path:
        slug = slugify(item["subject"])[:50] or "no-subject"
        filename = f"email-{slug}-{item['id'][:8]}.md"
        path = self.needs_action_dir / filename
        content = f"""---
type: email
from: {item['from']}
subject: {item['subject']}
date: {item['date']}
priority: normal
gmail_id: {item['id']}
---

# New Email: {item['subject']}

**From:** {item['from']}
**Date:** {item['date']}
**Labels:** {', '.join(item.get('labels', []))}

## Body
{item['body']}

## Suggested Actions
- [ ] Reply
- [ ] Forward
- [ ] Archive
"""
        path.write_text(content, encoding="utf-8")
        logger.info(f"Created action file: {path.name}")
        log_action(
            logs_dir=self.vault_path / "Logs",
            actor="gmail_watcher",
            action="email_detected",
            source=item["id"],
            result=f"action_file_created:{filename}",
        )
        self.mark_as_processed(item["id"])
        return path

    def mark_as_processed(self, message_id: str) -> None:
        label_id = self._get_or_create_label()
        if label_id:
            try:
                self.service.users().messages().modify(
                    userId="me", id=message_id, body={"addLabelIds": [label_id]}
                ).execute()
            except Exception as e:
                logger.error(f"Failed to label message {message_id}: {e}")

    def _get_or_create_label(self) -> str | None:
        if self._processed_label_id:
            return self._processed_label_id
        try:
            labels = self.service.users().labels().list(userId="me").execute().get("labels", [])
            for label in labels:
                if label["name"] == PROCESSED_LABEL:
                    self._processed_label_id = label["id"]
                    return label["id"]
            result = self.service.users().labels().create(userId="me", body={"name": PROCESSED_LABEL}).execute()
            self._processed_label_id = result["id"]
            return result["id"]
        except Exception as e:
            logger.error(f"Failed to get/create label: {e}")
            return None

    @staticmethod
    def _parse_message(msg: dict) -> dict:
        headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
        body = ""
        payload = msg.get("payload", {})
        if "body" in payload and payload["body"].get("data"):
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
        elif "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                    break
        return {
            "id": msg["id"],
            "from": headers.get("from", "unknown"),
            "subject": headers.get("subject", "(no subject)"),
            "date": headers.get("date", datetime.now(timezone.utc).isoformat()),
            "body": body,
            "labels": msg.get("labelIds", []),
        }
