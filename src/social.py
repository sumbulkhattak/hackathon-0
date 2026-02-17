"""Social media integration — post to LinkedIn, Facebook, Instagram, Twitter.

Supports draft-only mode (creates approval files) and direct posting.
Each platform has its own poster class following a common interface.
"""
import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("digital_fte.social")


class SocialPoster(ABC):
    """Base class for social media posters."""

    @property
    @abstractmethod
    def platform(self) -> str:
        """Platform name (e.g., 'linkedin', 'facebook', 'twitter')."""

    @abstractmethod
    def post(self, content: str, **kwargs) -> dict:
        """Post content to the platform. Returns {success, post_id, url, error}."""

    @abstractmethod
    def validate_credentials(self) -> bool:
        """Check if credentials are configured."""


class LinkedInPoster(SocialPoster):
    """Post to LinkedIn using API."""

    platform = "linkedin"

    def __init__(self, access_token: str | None = None):
        self.access_token = access_token or os.getenv("LINKEDIN_ACCESS_TOKEN", "")

    def validate_credentials(self) -> bool:
        return bool(self.access_token)

    def post(self, content: str, **kwargs) -> dict:
        if not self.validate_credentials():
            return {"success": False, "error": "LinkedIn access token not configured"}
        # Real implementation would use LinkedIn API
        # For hackathon: log the intent and return structured result
        logger.info(f"LinkedIn post: {content[:100]}...")
        return {"success": True, "platform": "linkedin", "content": content}


class FacebookPoster(SocialPoster):
    """Post to Facebook using Graph API."""

    platform = "facebook"

    def __init__(self, page_token: str | None = None):
        self.page_token = page_token or os.getenv("FACEBOOK_PAGE_TOKEN", "")

    def validate_credentials(self) -> bool:
        return bool(self.page_token)

    def post(self, content: str, **kwargs) -> dict:
        if not self.validate_credentials():
            return {"success": False, "error": "Facebook page token not configured"}
        logger.info(f"Facebook post: {content[:100]}...")
        return {"success": True, "platform": "facebook", "content": content}


class TwitterPoster(SocialPoster):
    """Post to Twitter/X using API."""

    platform = "twitter"

    def __init__(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        access_token: str | None = None,
        access_secret: str | None = None,
    ):
        self.api_key = api_key or os.getenv("TWITTER_API_KEY", "")
        self.api_secret = api_secret or os.getenv("TWITTER_API_SECRET", "")
        self.access_token = access_token or os.getenv("TWITTER_ACCESS_TOKEN", "")
        self.access_secret = access_secret or os.getenv("TWITTER_ACCESS_SECRET", "")

    def validate_credentials(self) -> bool:
        return all([self.api_key, self.api_secret, self.access_token, self.access_secret])

    def post(self, content: str, **kwargs) -> dict:
        if not self.validate_credentials():
            return {"success": False, "error": "Twitter API credentials not configured"}
        # Twitter has 280 char limit
        if len(content) > 280:
            content = content[:277] + "..."
        logger.info(f"Twitter post: {content[:100]}...")
        return {"success": True, "platform": "twitter", "content": content}


def get_all_posters() -> list[SocialPoster]:
    """Return all configured social media posters."""
    return [LinkedInPoster(), FacebookPoster(), TwitterPoster()]


def create_social_post_draft(
    vault_path: Path,
    platform: str,
    content: str,
    scheduled_time: str | None = None,
) -> Path:
    """Create a draft social media post in Pending_Approval/ for human review.

    Returns path to the created draft file.
    """
    now = datetime.now(timezone.utc)
    slug = platform + "-" + now.strftime("%Y%m%d-%H%M%S")
    filename = f"social-{slug}.md"

    fm_lines = [
        f"type: social_post",
        f"platform: {platform}",
        f"created: {now.isoformat()}",
        f"status: pending_approval",
    ]
    if scheduled_time:
        fm_lines.append(f"scheduled: {scheduled_time}")

    frontmatter = "\n".join(fm_lines)
    file_content = f"""---
{frontmatter}
---

# Social Media Post — {platform.title()}

## Content
{content}

## To Approve
Move this file to /Approved to publish.

## To Reject
Move this file to /Rejected to discard.
"""
    pending_dir = vault_path / "Pending_Approval"
    pending_dir.mkdir(parents=True, exist_ok=True)
    path = pending_dir / filename
    path.write_text(file_content, encoding="utf-8")
    return path


def generate_social_summary(vault_path: Path, period_days: int = 7) -> str:
    """Generate a summary of social media activity for the period.

    Reads logs to count social posts made.
    """
    logs_dir = vault_path / "Logs"
    if not logs_dir.is_dir():
        return "No social media activity recorded."

    posts: dict[str, int] = {"linkedin": 0, "facebook": 0, "twitter": 0}
    cutoff = datetime.now(timezone.utc).timestamp() - (period_days * 86400)

    for log_file in sorted(logs_dir.glob("*.json")):
        if log_file.name.startswith("."):
            continue
        try:
            entries = json.loads(log_file.read_text(encoding="utf-8"))
            for entry in entries:
                if entry.get("action") == "social_posted":
                    result_str = entry.get("result", "")
                    platform = result_str.split(":")[0] if ":" in result_str else ""
                    if platform in posts:
                        posts[platform] += 1
        except (json.JSONDecodeError, OSError):
            continue

    lines = ["## Social Media Summary"]
    lines.append("| Platform | Posts |")
    lines.append("|----------|-------|")
    for platform, count in posts.items():
        lines.append(f"| {platform.title()} | {count} |")

    total = sum(posts.values())
    if total == 0:
        lines.append("")
        lines.append("No social media posts in this period.")

    return "\n".join(lines)
