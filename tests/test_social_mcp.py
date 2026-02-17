"""Tests for the Social Media MCP Server tools."""
import json
from pathlib import Path

import pytest

# We test the tool functions directly (not via MCP protocol)
import mcp_servers.social_server as social_server


@pytest.fixture(autouse=True)
def set_vault_path(tmp_path):
    """Override vault path for all tests."""
    for folder in [
        "Inbox", "Needs_Action", "Plans", "Pending_Approval",
        "Approved", "Done", "Logs", "Incoming_Files", "Rejected",
    ]:
        (tmp_path / folder).mkdir()
    social_server.VAULT_PATH = tmp_path
    yield tmp_path


# --- create_draft_post tests ---


def test_create_draft_post_creates_file(set_vault_path):
    result = json.loads(social_server.create_draft_post(
        platform="linkedin", content="Check out our new product!",
    ))
    assert result["success"] is True
    assert result["platform"] == "linkedin"
    assert "draft_path" in result
    # Verify the file actually exists
    draft_path = Path(result["draft_path"])
    assert draft_path.exists()
    text = draft_path.read_text(encoding="utf-8")
    assert "Check out our new product!" in text


# --- get_social_summary tests ---


def test_get_social_summary_returns_json(set_vault_path):
    result = json.loads(social_server.get_social_summary())
    assert result["success"] is True
    assert "summary" in result
    assert "## Social Media Summary" in result["summary"]


# --- post_to_linkedin tests ---


def test_post_to_linkedin_no_creds(set_vault_path, monkeypatch):
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "")
    result = json.loads(social_server.post_to_linkedin(content="Test post"))
    assert result["success"] is False
    assert "not configured" in result["error"]


# --- post_to_facebook tests ---


def test_post_to_facebook_no_creds(set_vault_path, monkeypatch):
    monkeypatch.setenv("FACEBOOK_PAGE_TOKEN", "")
    result = json.loads(social_server.post_to_facebook(content="Test post"))
    assert result["success"] is False
    assert "not configured" in result["error"]


# --- post_to_twitter tests ---


def test_post_to_twitter_no_creds(set_vault_path, monkeypatch):
    monkeypatch.setenv("TWITTER_API_KEY", "")
    monkeypatch.setenv("TWITTER_API_SECRET", "")
    monkeypatch.setenv("TWITTER_ACCESS_TOKEN", "")
    monkeypatch.setenv("TWITTER_ACCESS_SECRET", "")
    result = json.loads(social_server.post_to_twitter(content="Test post"))
    assert result["success"] is False
    assert "not configured" in result["error"]
