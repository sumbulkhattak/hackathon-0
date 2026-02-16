"""Tests for the file system watcher."""
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from src.watchers.file_watcher import FileWatcher

SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"}


@pytest.fixture
def vault(tmp_path):
    for folder in ["Incoming_Files", "Needs_Action", "Logs"]:
        (tmp_path / folder).mkdir()
    return tmp_path


@pytest.fixture
def watcher(vault):
    return FileWatcher(vault_path=vault)


def _drop_file(vault, name="report.pdf", content=b"fake-pdf"):
    path = vault / "Incoming_Files" / name
    path.write_bytes(content)
    return path


# --- Detection ---

def test_detects_new_pdf(watcher, vault):
    """check_for_updates should find new PDF files."""
    _drop_file(vault, "report.pdf")
    items = watcher.check_for_updates()
    assert len(items) == 1
    assert items[0]["filename"] == "report.pdf"
    assert items[0]["extension"] == ".pdf"


def test_detects_new_image(watcher, vault):
    """check_for_updates should find new image files."""
    _drop_file(vault, "photo.png")
    items = watcher.check_for_updates()
    assert len(items) == 1
    assert items[0]["filename"] == "photo.png"
    assert items[0]["extension"] == ".png"


def test_ignores_unsupported_extensions(watcher, vault):
    """check_for_updates should skip files that aren't PDFs or images."""
    _drop_file(vault, "notes.txt")
    _drop_file(vault, "data.csv")
    items = watcher.check_for_updates()
    assert len(items) == 0


def test_detects_multiple_files(watcher, vault):
    """check_for_updates should return all supported files."""
    _drop_file(vault, "a.pdf")
    _drop_file(vault, "b.jpg")
    _drop_file(vault, "c.txt")  # ignored
    items = watcher.check_for_updates()
    assert len(items) == 2


def test_does_not_redetect_processed_files(watcher, vault):
    """check_for_updates should skip files already processed."""
    _drop_file(vault, "report.pdf")
    watcher.run_once()
    items = watcher.check_for_updates()
    assert len(items) == 0


# --- Action file creation ---

def test_creates_action_file(watcher, vault):
    """create_action_file should write a markdown file in Needs_Action."""
    _drop_file(vault, "invoice.pdf")
    items = watcher.check_for_updates()
    path = watcher.create_action_file(items[0])
    assert path.exists()
    assert path.parent.name == "Needs_Action"
    assert path.suffix == ".md"


def test_action_file_has_frontmatter(watcher, vault):
    """Action file should contain YAML frontmatter with metadata."""
    _drop_file(vault, "scan.jpg")
    items = watcher.check_for_updates()
    path = watcher.create_action_file(items[0])
    content = path.read_text()
    assert "type: file" in content
    assert "filename: scan.jpg" in content
    assert "extension: .jpg" in content


def test_action_file_has_timestamp(watcher, vault):
    """Action file should include a detected_at timestamp."""
    _drop_file(vault, "doc.pdf")
    items = watcher.check_for_updates()
    path = watcher.create_action_file(items[0])
    content = path.read_text()
    assert "detected_at:" in content


def test_action_file_has_placeholder_summary(watcher, vault):
    """Action file should include a placeholder summary section."""
    _drop_file(vault, "chart.png")
    items = watcher.check_for_updates()
    path = watcher.create_action_file(items[0])
    content = path.read_text()
    assert "## Summary" in content
    assert "Placeholder" in content or "pending" in content.lower()


# --- Dry-run mode ---

def test_dry_run_does_not_create_action_file(vault):
    """In dry-run mode, no action file should be created."""
    watcher = FileWatcher(vault_path=vault, dry_run=True)
    _drop_file(vault, "report.pdf")
    count = watcher.run_once()
    assert count == 0
    action_files = list((vault / "Needs_Action").glob("*.md"))
    assert len(action_files) == 0


def test_dry_run_logs_detection(vault, caplog):
    """In dry-run mode, detected files should be logged."""
    watcher = FileWatcher(vault_path=vault, dry_run=True)
    _drop_file(vault, "report.pdf")
    with caplog.at_level("INFO"):
        watcher.check_for_updates()
    assert any("DRY-RUN" in r.message for r in caplog.records)


# --- Logging ---

def test_logs_file_detection(watcher, vault, caplog):
    """Watcher should log when a new file is detected."""
    _drop_file(vault, "memo.pdf")
    with caplog.at_level("INFO"):
        watcher.run_once()
    assert any("memo.pdf" in r.message for r in caplog.records)


# --- run_once integration ---

def test_run_once_returns_count(watcher, vault):
    """run_once should return the number of files processed."""
    _drop_file(vault, "a.pdf")
    _drop_file(vault, "b.png")
    count = watcher.run_once()
    assert count == 2


def test_run_once_moves_processed_files(watcher, vault):
    """After run_once, processed files should be moved out of Incoming_Files."""
    src_file = _drop_file(vault, "report.pdf")
    watcher.run_once()
    assert not src_file.exists()
