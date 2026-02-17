"""Tests for the social media posting module (src/social.py)."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.social import (
    LinkedInPoster,
    FacebookPoster,
    TwitterPoster,
    get_all_posters,
    create_social_post_draft,
    generate_social_summary,
)


# --- LinkedInPoster tests ---


def test_linkedin_poster_platform_name():
    poster = LinkedInPoster(access_token="")
    assert poster.platform == "linkedin"


def test_linkedin_poster_no_credentials():
    poster = LinkedInPoster(access_token="")
    result = poster.post("Hello LinkedIn!")
    assert result["success"] is False
    assert "not configured" in result["error"]


def test_linkedin_poster_with_credentials():
    poster = LinkedInPoster(access_token="test-token-123")
    result = poster.post("Hello LinkedIn!")
    assert result["success"] is True
    assert result["platform"] == "linkedin"
    assert result["content"] == "Hello LinkedIn!"


# --- FacebookPoster tests ---


def test_facebook_poster_no_credentials():
    poster = FacebookPoster(page_token="")
    result = poster.post("Hello Facebook!")
    assert result["success"] is False
    assert "not configured" in result["error"]


def test_facebook_poster_with_credentials():
    poster = FacebookPoster(page_token="test-page-token")
    result = poster.post("Hello Facebook!")
    assert result["success"] is True
    assert result["platform"] == "facebook"
    assert result["content"] == "Hello Facebook!"


# --- TwitterPoster tests ---


def test_twitter_poster_no_credentials():
    poster = TwitterPoster(api_key="", api_secret="", access_token="", access_secret="")
    result = poster.post("Hello Twitter!")
    assert result["success"] is False
    assert "not configured" in result["error"]


def test_twitter_poster_with_credentials():
    poster = TwitterPoster(
        api_key="key", api_secret="secret",
        access_token="token", access_secret="asecret",
    )
    result = poster.post("Hello Twitter!")
    assert result["success"] is True
    assert result["platform"] == "twitter"
    assert result["content"] == "Hello Twitter!"


def test_twitter_poster_truncates_long_content():
    poster = TwitterPoster(
        api_key="key", api_secret="secret",
        access_token="token", access_secret="asecret",
    )
    long_content = "A" * 300
    result = poster.post(long_content)
    assert result["success"] is True
    assert len(result["content"]) == 280
    assert result["content"].endswith("...")


# --- get_all_posters tests ---


def test_get_all_posters_returns_three():
    posters = get_all_posters()
    assert len(posters) == 3
    platforms = [p.platform for p in posters]
    assert "linkedin" in platforms
    assert "facebook" in platforms
    assert "twitter" in platforms


# --- create_social_post_draft tests ---


def test_create_social_post_draft_creates_file(tmp_path):
    path = create_social_post_draft(tmp_path, "linkedin", "Test post content")
    assert path.exists()
    assert path.suffix == ".md"
    assert "social-linkedin-" in path.name


def test_create_social_post_draft_has_frontmatter(tmp_path):
    path = create_social_post_draft(tmp_path, "facebook", "Test post")
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---")
    assert "platform: facebook" in text
    assert "type: social_post" in text
    assert "status: pending_approval" in text


def test_create_social_post_draft_includes_content(tmp_path):
    content = "This is a great social media post about our product launch!"
    path = create_social_post_draft(tmp_path, "twitter", content)
    text = path.read_text(encoding="utf-8")
    assert content in text
    assert "## Content" in text
    assert "Twitter" in text


# --- generate_social_summary tests ---


def test_generate_social_summary_empty(tmp_path):
    summary = generate_social_summary(tmp_path)
    assert "No social media activity recorded." in summary


def test_generate_social_summary_with_posts(tmp_path):
    logs_dir = tmp_path / "Logs"
    logs_dir.mkdir()
    entries = [
        {
            "timestamp": "2026-02-17T10:00:00+00:00",
            "actor": "mcp_social_server",
            "action": "social_posted",
            "source": "mcp_tool",
            "result": "linkedin:Test post",
        },
        {
            "timestamp": "2026-02-17T11:00:00+00:00",
            "actor": "mcp_social_server",
            "action": "social_posted",
            "source": "mcp_tool",
            "result": "twitter:Another post",
        },
    ]
    log_file = logs_dir / "2026-02-17.json"
    log_file.write_text(json.dumps(entries), encoding="utf-8")

    summary = generate_social_summary(tmp_path)
    assert "## Social Media Summary" in summary
    assert "| Linkedin | 1 |" in summary
    assert "| Twitter | 1 |" in summary
    assert "No social media posts" not in summary
