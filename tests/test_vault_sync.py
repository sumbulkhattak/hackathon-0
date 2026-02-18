"""Tests for vault sync — git-based cloud/local synchronization."""
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture
def vault(tmp_path):
    """Create a vault directory structure."""
    for folder in ["Needs_Action", "Pending_Approval", "Approved", "Rejected", "Done"]:
        (tmp_path / folder).mkdir()
    return tmp_path


@pytest.fixture
def git_vault(vault):
    """Create a vault that is also a git repo."""
    subprocess.run(["git", "init"], cwd=str(vault), capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(vault), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(vault), capture_output=True)
    # Initial commit so we have a HEAD
    (vault / ".gitkeep").write_text("")
    subprocess.run(["git", "add", "-A"], cwd=str(vault), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(vault), capture_output=True)
    return vault


def test_is_git_repo_true(git_vault):
    """is_git_repo should return True for a git repository."""
    from src.vault_sync import is_git_repo
    assert is_git_repo(git_vault) is True


def test_is_git_repo_false(vault):
    """is_git_repo should return False for a non-git directory."""
    from src.vault_sync import is_git_repo
    assert is_git_repo(vault) is False


def test_init_sync_creates_repo(vault):
    """init_sync should initialize a git repo and return True."""
    from src.vault_sync import init_sync, is_git_repo
    result = init_sync(vault)
    assert result is True
    assert is_git_repo(vault) is True


def test_init_sync_skips_existing_repo(git_vault):
    """init_sync should return False if repo already exists."""
    from src.vault_sync import init_sync
    result = init_sync(git_vault)
    assert result is False


def test_get_sync_status_no_repo(vault):
    """get_sync_status should return default values for non-repo."""
    from src.vault_sync import get_sync_status
    status = get_sync_status(vault)
    assert status["is_repo"] is False
    assert status["has_remote"] is False
    assert status["pending_changes"] == 0
    assert status["last_sync"] == "never"


def test_get_sync_status_git_repo(git_vault):
    """get_sync_status should report repo status correctly."""
    from src.vault_sync import get_sync_status
    status = get_sync_status(git_vault)
    assert status["is_repo"] is True
    assert status["has_remote"] is False
    assert status["pending_changes"] == 0
    assert status["last_sync"] == "init"


def test_get_sync_status_pending_changes(git_vault):
    """get_sync_status should count uncommitted changes."""
    from src.vault_sync import get_sync_status
    (git_vault / "Needs_Action" / "new-item.md").write_text("# New item")
    status = get_sync_status(git_vault)
    assert status["pending_changes"] >= 1


def test_push_vault_commits_changes(git_vault):
    """push_vault should commit new files."""
    from src.vault_sync import push_vault
    (git_vault / "Pending_Approval" / "draft-plan.md").write_text("# Draft")
    result = push_vault(git_vault, "test sync push")
    assert result is True
    # Verify committed
    log = subprocess.run(
        ["git", "log", "-1", "--format=%s"],
        cwd=str(git_vault), capture_output=True, text=True,
    )
    assert "test sync push" in log.stdout


def test_push_vault_no_changes(git_vault):
    """push_vault should return False when nothing to commit."""
    from src.vault_sync import push_vault
    result = push_vault(git_vault, "empty")
    assert result is False


def test_push_vault_requires_repo(vault):
    """push_vault should raise VaultSyncError if not a repo."""
    from src.vault_sync import push_vault, VaultSyncError
    with pytest.raises(VaultSyncError, match="not a git repository"):
        push_vault(vault)


def test_pull_vault_no_remote(git_vault):
    """pull_vault should return False if no remote is configured."""
    from src.vault_sync import pull_vault
    result = pull_vault(git_vault)
    assert result is False


def test_pull_vault_requires_repo(vault):
    """pull_vault should raise VaultSyncError if not a repo."""
    from src.vault_sync import pull_vault, VaultSyncError
    with pytest.raises(VaultSyncError, match="not a git repository"):
        pull_vault(vault)


def test_sync_vault_no_remote(git_vault):
    """sync_vault should work even without a remote (commit-only)."""
    from src.vault_sync import sync_vault
    (git_vault / "Needs_Action" / "item.md").write_text("# Item")
    result = sync_vault(git_vault, "sync test")
    assert result["pulled"] is False  # No remote
    assert result["pushed"] is True   # Local changes committed


def test_claim_item_moves_file(vault):
    """claim_item should move a file between folders."""
    from src.vault_sync import claim_item
    (vault / "Pending_Approval" / "plan-test.md").write_text("# Plan")
    result = claim_item(vault, "plan-test.md", "Pending_Approval", "Approved")
    assert result == vault / "Approved" / "plan-test.md"
    assert result.exists()
    assert not (vault / "Pending_Approval" / "plan-test.md").exists()


def test_claim_item_missing_source(vault):
    """claim_item should raise VaultSyncError if source file doesn't exist."""
    from src.vault_sync import claim_item, VaultSyncError
    with pytest.raises(VaultSyncError, match="not found"):
        claim_item(vault, "nonexistent.md", "Pending_Approval", "Approved")


def test_claim_item_duplicate_target(vault):
    """claim_item should raise VaultSyncError if target already exists."""
    from src.vault_sync import claim_item, VaultSyncError
    (vault / "Pending_Approval" / "plan-dup.md").write_text("# Draft")
    (vault / "Approved" / "plan-dup.md").write_text("# Already here")
    with pytest.raises(VaultSyncError, match="already exists"):
        claim_item(vault, "plan-dup.md", "Pending_Approval", "Approved")


def test_claim_item_reject(vault):
    """claim_item should support moving to Rejected/ folder."""
    from src.vault_sync import claim_item
    (vault / "Pending_Approval" / "plan-bad.md").write_text("# Bad plan")
    result = claim_item(vault, "plan-bad.md", "Pending_Approval", "Rejected")
    assert result == vault / "Rejected" / "plan-bad.md"
    assert result.exists()


def test_vault_sync_error_is_exception():
    """VaultSyncError should be a proper exception."""
    from src.vault_sync import VaultSyncError
    with pytest.raises(VaultSyncError):
        raise VaultSyncError("test error")


# --- Platinum tier: In_Progress claim-by-move ---


def test_claim_to_in_progress(vault):
    """claim_to_in_progress should move a file from Needs_Action to In_Progress/<agent>/."""
    from src.vault_sync import claim_to_in_progress
    (vault / "Needs_Action" / "email-task.md").write_text("# Task")
    result = claim_to_in_progress(vault, "email-task.md", "cloud_agent")
    assert result == vault / "In_Progress" / "cloud_agent" / "email-task.md"
    assert result.exists()
    assert not (vault / "Needs_Action" / "email-task.md").exists()


def test_claim_to_in_progress_already_claimed(vault):
    """claim_to_in_progress should reject if another agent already claimed the file."""
    from src.vault_sync import claim_to_in_progress, VaultSyncError
    (vault / "Needs_Action" / "email-dup.md").write_text("# Task")
    # First agent claims it
    (vault / "In_Progress" / "other_agent").mkdir(parents=True)
    (vault / "In_Progress" / "other_agent" / "email-dup.md").write_text("# Claimed")
    with pytest.raises(VaultSyncError, match="already claimed"):
        claim_to_in_progress(vault, "email-dup.md", "cloud_agent")


def test_claim_to_in_progress_missing_source(vault):
    """claim_to_in_progress should raise if source file doesn't exist."""
    from src.vault_sync import claim_to_in_progress, VaultSyncError
    with pytest.raises(VaultSyncError, match="not found"):
        claim_to_in_progress(vault, "nonexistent.md", "cloud_agent")


# --- Platinum tier: Updates (cloud writes, local merges) ---


def test_write_update(vault):
    """write_update should create a file in Updates/."""
    from src.vault_sync import write_update
    result = write_update(vault, "status-2026-02-18.md", "Cloud processed 5 emails")
    assert result == vault / "Updates" / "status-2026-02-18.md"
    assert result.exists()
    assert result.read_text(encoding="utf-8") == "Cloud processed 5 emails"


def test_merge_updates(vault):
    """merge_updates should merge Updates/ files into Dashboard.md and remove them."""
    from src.vault_sync import merge_updates
    (vault / "Updates").mkdir(exist_ok=True)
    (vault / "Updates" / "update-1.md").write_text("Five emails triaged")
    (vault / "Updates" / "update-2.md").write_text("Two drafts created")
    (vault / "Dashboard.md").write_text("# Dashboard\nExisting content")

    count = merge_updates(vault)
    assert count == 2
    # Updates removed
    assert not (vault / "Updates" / "update-1.md").exists()
    assert not (vault / "Updates" / "update-2.md").exists()
    # Dashboard updated
    dashboard = (vault / "Dashboard.md").read_text(encoding="utf-8")
    assert "Five emails triaged" in dashboard
    assert "Two drafts created" in dashboard
    assert "Existing content" in dashboard


def test_merge_updates_no_updates(vault):
    """merge_updates should return 0 when no updates exist."""
    from src.vault_sync import merge_updates
    count = merge_updates(vault)
    assert count == 0
