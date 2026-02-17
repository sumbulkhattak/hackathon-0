"""Social Media MCP Server — exposes social posting as tools for Claude Code.

This MCP server provides:
- post_to_linkedin: Post content to LinkedIn
- post_to_facebook: Post content to Facebook
- post_to_twitter: Post content to Twitter (280 char limit)
- create_draft_post: Create draft in Pending_Approval/ for human review
- get_social_summary: Summary of social media activity

Usage:
    python mcp_servers/social_server.py
"""
import json
import logging
import os
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.social import (
    LinkedInPoster,
    FacebookPoster,
    TwitterPoster,
    create_social_post_draft,
    generate_social_summary,
)
from src.utils import log_action

logger = logging.getLogger("mcp.social_server")

mcp = FastMCP("Digital FTE Social Media Server")

# Vault path from environment
VAULT_PATH = Path(os.getenv("VAULT_PATH", "./vault")).resolve()


@mcp.tool()
def post_to_linkedin(content: str) -> str:
    """Post content to LinkedIn.

    Args:
        content: The text content to post to LinkedIn.
    """
    logs_dir = VAULT_PATH / "Logs"
    poster = LinkedInPoster()
    result = poster.post(content)

    if result.get("success"):
        log_action(
            logs_dir=logs_dir,
            actor="mcp_social_server",
            action="social_posted",
            source="mcp_tool",
            result=f"linkedin:{content[:50]}",
        )

    return json.dumps(result)


@mcp.tool()
def post_to_facebook(content: str) -> str:
    """Post content to Facebook.

    Args:
        content: The text content to post to Facebook.
    """
    logs_dir = VAULT_PATH / "Logs"
    poster = FacebookPoster()
    result = poster.post(content)

    if result.get("success"):
        log_action(
            logs_dir=logs_dir,
            actor="mcp_social_server",
            action="social_posted",
            source="mcp_tool",
            result=f"facebook:{content[:50]}",
        )

    return json.dumps(result)


@mcp.tool()
def post_to_twitter(content: str) -> str:
    """Post content to Twitter/X (280 character limit, auto-truncated).

    Args:
        content: The text content to post to Twitter (max 280 chars).
    """
    logs_dir = VAULT_PATH / "Logs"
    poster = TwitterPoster()
    result = poster.post(content)

    if result.get("success"):
        log_action(
            logs_dir=logs_dir,
            actor="mcp_social_server",
            action="social_posted",
            source="mcp_tool",
            result=f"twitter:{content[:50]}",
        )

    return json.dumps(result)


@mcp.tool()
def create_draft_post(platform: str, content: str) -> str:
    """Create a draft social media post in Pending_Approval/ for human review.

    Args:
        platform: Target platform (linkedin, facebook, twitter).
        content: The text content for the social media post.
    """
    try:
        path = create_social_post_draft(VAULT_PATH, platform, content)
        log_action(
            logs_dir=VAULT_PATH / "Logs",
            actor="mcp_social_server",
            action="social_draft_created",
            source="mcp_tool",
            result=f"{platform}:{path.name}",
        )
        return json.dumps({
            "success": True,
            "platform": platform,
            "draft_path": str(path),
            "message": f"Draft created for {platform}. Review in Pending_Approval/.",
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
        })


@mcp.tool()
def get_social_summary() -> str:
    """Get a summary of social media posting activity for the past 7 days."""
    try:
        summary = generate_social_summary(VAULT_PATH, period_days=7)
        return json.dumps({
            "success": True,
            "summary": summary,
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
        })


if __name__ == "__main__":
    mcp.run()
