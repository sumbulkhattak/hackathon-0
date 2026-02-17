"""Email MCP Server — exposes email operations as tools for Claude Code.

This MCP server provides:
- send_email: Send a threaded Gmail reply
- search_emails: Search Gmail with a query
- list_pending: List files awaiting approval in the vault
- get_vault_status: Get current vault folder counts

Usage:
    python mcp_servers/email_server.py
"""
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.gmail_sender import send_reply, check_send_limit, increment_send_count
from src.dashboard import OVERVIEW_FOLDERS, _count_files
from src.utils import log_action, parse_frontmatter

logger = logging.getLogger("mcp.email_server")

mcp = FastMCP("Digital FTE Email Server")

# Vault path from environment
VAULT_PATH = Path(os.getenv("VAULT_PATH", "./vault")).resolve()
DAILY_SEND_LIMIT = int(os.getenv("DAILY_SEND_LIMIT", "20"))


def _get_gmail_service():
    """Lazy-load Gmail service to avoid import-time auth."""
    from src.auth import get_gmail_service
    credentials_dir = Path("credentials")
    return get_gmail_service(credentials_dir)


@mcp.tool()
def send_email(gmail_id: str, to: str, subject: str, body: str) -> str:
    """Send a threaded Gmail reply.

    Args:
        gmail_id: The Gmail message ID to reply to
        to: Recipient email address
        subject: Email subject line
        body: Reply body text
    """
    logs_dir = VAULT_PATH / "Logs"

    # Check daily send limit
    if not check_send_limit(logs_dir, DAILY_SEND_LIMIT):
        return json.dumps({
            "success": False,
            "error": f"Daily send limit ({DAILY_SEND_LIMIT}) reached",
        })

    try:
        gmail_service = _get_gmail_service()
        send_reply(
            gmail_service=gmail_service,
            gmail_id=gmail_id,
            to=to,
            subject=subject,
            body=body,
        )
        increment_send_count(logs_dir)
        log_action(
            logs_dir=logs_dir,
            actor="mcp_email_server",
            action="email_sent",
            source="mcp_tool",
            result=f"reply_to:{to}",
        )
        return json.dumps({
            "success": True,
            "message": f"Reply sent to {to}",
        })
    except Exception as e:
        log_action(
            logs_dir=logs_dir,
            actor="mcp_email_server",
            action="send_failed",
            source="mcp_tool",
            result=str(e),
        )
        return json.dumps({
            "success": False,
            "error": str(e),
        })


@mcp.tool()
def search_emails(query: str, max_results: int = 5) -> str:
    """Search Gmail for emails matching a query.

    Args:
        query: Gmail search query (e.g., 'is:unread', 'from:client@example.com')
        max_results: Maximum number of results to return (default 5)
    """
    try:
        gmail_service = _get_gmail_service()
        results = gmail_service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()
        messages = results.get("messages", [])

        email_list = []
        for msg_ref in messages:
            msg = gmail_service.users().messages().get(
                userId="me", id=msg_ref["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            ).execute()
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            email_list.append({
                "id": msg_ref["id"],
                "from": headers.get("From", ""),
                "subject": headers.get("Subject", ""),
                "date": headers.get("Date", ""),
                "snippet": msg.get("snippet", ""),
            })

        return json.dumps({
            "success": True,
            "count": len(email_list),
            "emails": email_list,
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
        })


@mcp.tool()
def list_pending() -> str:
    """List all files in the Pending_Approval vault folder awaiting human review."""
    pa_dir = VAULT_PATH / "Pending_Approval"
    if not pa_dir.is_dir():
        return json.dumps({"success": True, "pending": []})

    items = []
    for f in sorted(pa_dir.iterdir()):
        if f.is_file() and f.suffix == ".md":
            fm = parse_frontmatter(f)
            items.append({
                "filename": f.name,
                "source": fm.get("source", ""),
                "confidence": fm.get("confidence", "N/A"),
                "action": fm.get("action", "review"),
                "created": fm.get("created", ""),
            })

    return json.dumps({
        "success": True,
        "count": len(items),
        "pending": items,
    })


@mcp.tool()
def get_vault_status() -> str:
    """Get current vault folder counts and system status."""
    counts = {}
    total_active = 0
    active_folders = ["Inbox", "Needs_Action", "Pending_Approval", "Approved"]

    for folder in OVERVIEW_FOLDERS:
        count = _count_files(VAULT_PATH / folder)
        counts[folder] = count
        if folder in active_folders:
            total_active += count

    return json.dumps({
        "success": True,
        "status": "active" if total_active > 0 else "idle",
        "items_to_process": total_active,
        "folders": counts,
    })


if __name__ == "__main__":
    mcp.run()
