"""Vault sync — git-based synchronization for cloud/local split deployment.

Implements the claim-by-move protocol:
- Cloud zone writes drafts to Pending_Approval/
- Local zone claims items by moving them to Approved/ or Rejected/
- Single-writer rule: only one zone modifies a file at a time

Sync mechanism uses git as the transport layer:
- push_vault(): commit and push local changes
- pull_vault(): pull remote changes
- sync_vault(): pull then push (full cycle)
"""
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger("digital_fte.vault_sync")


class VaultSyncError(Exception):
    """Raised when vault sync operations fail."""


def _run_git(vault_path: Path, *args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    """Run a git command in the vault directory."""
    cmd = ["git"] + list(args)
    try:
        result = subprocess.run(
            cmd,
            cwd=str(vault_path),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result
    except subprocess.TimeoutExpired:
        raise VaultSyncError(f"Git command timed out: {' '.join(cmd)}")
    except FileNotFoundError:
        raise VaultSyncError("Git not found. Is git installed?")


def is_git_repo(vault_path: Path) -> bool:
    """Check if the vault path is inside a git repository."""
    result = _run_git(vault_path, "rev-parse", "--is-inside-work-tree")
    return result.returncode == 0 and result.stdout.strip() == "true"


def init_sync(vault_path: Path) -> bool:
    """Initialize git repo in vault if not already a repo.

    Returns True if initialized, False if already a repo.
    """
    if is_git_repo(vault_path):
        return False
    result = _run_git(vault_path, "init")
    if result.returncode != 0:
        raise VaultSyncError(f"Failed to init git repo: {result.stderr}")
    logger.info(f"Initialized git repo in {vault_path}")
    return True


def get_sync_status(vault_path: Path) -> dict:
    """Get the current sync status of the vault.

    Returns dict with:
    - is_repo: bool
    - has_remote: bool
    - pending_changes: int (number of uncommitted changes)
    - last_sync: str (last commit message or "never")
    """
    status = {
        "is_repo": False,
        "has_remote": False,
        "pending_changes": 0,
        "last_sync": "never",
    }

    if not is_git_repo(vault_path):
        return status

    status["is_repo"] = True

    # Check for remote
    result = _run_git(vault_path, "remote")
    status["has_remote"] = bool(result.stdout.strip())

    # Count pending changes
    result = _run_git(vault_path, "status", "--porcelain")
    if result.returncode == 0:
        lines = [l for l in result.stdout.strip().split("\n") if l.strip()]
        status["pending_changes"] = len(lines)

    # Last commit
    result = _run_git(vault_path, "log", "-1", "--format=%s")
    if result.returncode == 0 and result.stdout.strip():
        status["last_sync"] = result.stdout.strip()

    return status


def push_vault(vault_path: Path, message: str = "vault sync") -> bool:
    """Commit and push local vault changes.

    Returns True if changes were pushed, False if nothing to push.
    """
    if not is_git_repo(vault_path):
        raise VaultSyncError("Vault is not a git repository. Run init_sync() first.")

    # Stage all changes
    result = _run_git(vault_path, "add", "-A")
    if result.returncode != 0:
        raise VaultSyncError(f"Failed to stage changes: {result.stderr}")

    # Check if there are changes to commit
    result = _run_git(vault_path, "status", "--porcelain")
    if not result.stdout.strip():
        logger.info("No changes to push")
        return False

    # Commit
    result = _run_git(vault_path, "commit", "-m", message)
    if result.returncode != 0:
        raise VaultSyncError(f"Failed to commit: {result.stderr}")

    # Push (only if remote exists)
    remote_result = _run_git(vault_path, "remote")
    if remote_result.stdout.strip():
        result = _run_git(vault_path, "push", timeout=60)
        if result.returncode != 0:
            raise VaultSyncError(f"Failed to push: {result.stderr}")
        logger.info(f"Pushed vault changes: {message}")
    else:
        logger.info(f"Committed vault changes (no remote): {message}")

    return True


def pull_vault(vault_path: Path) -> bool:
    """Pull remote vault changes.

    Returns True if new changes were pulled, False if already up to date.
    """
    if not is_git_repo(vault_path):
        raise VaultSyncError("Vault is not a git repository. Run init_sync() first.")

    # Check for remote
    result = _run_git(vault_path, "remote")
    if not result.stdout.strip():
        logger.info("No remote configured, skipping pull")
        return False

    result = _run_git(vault_path, "pull", "--rebase", timeout=60)
    if result.returncode != 0:
        raise VaultSyncError(f"Failed to pull: {result.stderr}")

    already_up_to_date = "Already up to date" in result.stdout or "Already up-to-date" in result.stdout
    if already_up_to_date:
        logger.info("Vault already up to date")
        return False

    logger.info("Pulled new vault changes")
    return True


def sync_vault(vault_path: Path, message: str = "vault sync") -> dict:
    """Full sync cycle: pull then push.

    Returns dict with:
    - pulled: bool (new changes pulled)
    - pushed: bool (local changes pushed)
    """
    pulled = pull_vault(vault_path)
    pushed = push_vault(vault_path, message)
    return {"pulled": pulled, "pushed": pushed}


def claim_item(vault_path: Path, filename: str, from_folder: str, to_folder: str) -> Path:
    """Claim an item by moving it between folders (claim-by-move protocol).

    This is the core of the single-writer protocol:
    - Cloud writes to Pending_Approval/
    - Local claims by moving to Approved/ or Rejected/

    Returns the new path of the claimed file.
    """
    source = vault_path / from_folder / filename
    if not source.exists():
        raise VaultSyncError(f"Item not found: {source}")

    dest_dir = vault_path / to_folder
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename

    if dest.exists():
        raise VaultSyncError(f"Item already exists in {to_folder}: {filename}")

    source.rename(dest)
    logger.info(f"Claimed {filename}: {from_folder} → {to_folder}")
    return dest


def claim_to_in_progress(vault_path: Path, filename: str, agent_name: str) -> Path:
    """Claim an item from Needs_Action to In_Progress/<agent>/ (Platinum protocol).

    First agent to move an item from Needs_Action to In_Progress/<agent>/ owns it;
    other agents must ignore it.

    Returns the new path of the claimed file.
    """
    source = vault_path / "Needs_Action" / filename
    if not source.exists():
        raise VaultSyncError(f"Item not found: {source}")

    # Check if any agent already claimed this file
    in_progress_dir = vault_path / "In_Progress"
    if in_progress_dir.is_dir():
        for agent_dir in in_progress_dir.iterdir():
            if agent_dir.is_dir() and (agent_dir / filename).exists():
                raise VaultSyncError(
                    f"Item already claimed by {agent_dir.name}: {filename}"
                )

    dest_dir = vault_path / "In_Progress" / agent_name
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename

    source.rename(dest)
    logger.info(f"Agent '{agent_name}' claimed {filename} to In_Progress")
    return dest


def write_update(vault_path: Path, filename: str, content: str) -> Path:
    """Cloud writes an update to Updates/ for Local to merge into Dashboard.md.

    Cloud zone uses this instead of writing Dashboard.md directly
    (single-writer rule: only Local writes Dashboard.md).
    """
    updates_dir = vault_path / "Updates"
    updates_dir.mkdir(parents=True, exist_ok=True)
    dest = updates_dir / filename
    dest.write_text(content, encoding="utf-8")
    logger.info(f"Cloud wrote update: {filename}")
    return dest


def merge_updates(vault_path: Path) -> int:
    """Local merges pending Updates/ into Dashboard.md and removes processed updates.

    Returns the number of updates merged.
    """
    updates_dir = vault_path / "Updates"
    if not updates_dir.is_dir():
        return 0

    update_files = sorted(updates_dir.glob("*.md"))
    if not update_files:
        return 0

    dashboard_path = vault_path / "Dashboard.md"
    dashboard_content = ""
    if dashboard_path.exists():
        dashboard_content = dashboard_path.read_text(encoding="utf-8")

    merged = 0
    for update_file in update_files:
        update_content = update_file.read_text(encoding="utf-8")
        # Append update as a new section
        dashboard_content += f"\n\n## Update: {update_file.stem}\n{update_content}"
        update_file.unlink()
        merged += 1
        logger.info(f"Merged update into Dashboard.md: {update_file.name}")

    if merged > 0:
        dashboard_path.write_text(dashboard_content, encoding="utf-8")
        logger.info(f"Merged {merged} update(s) into Dashboard.md")

    return merged
