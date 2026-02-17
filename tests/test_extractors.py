"""Tests for file content extractors."""
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


def _create_test_pdf(path: Path, text: str = "Invoice #2026-001\nAmount: $1,500.00\nDue: 2026-03-15") -> Path:
    """Create a minimal PDF file with the given text using pymupdf."""
    import pymupdf
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()
    return path


def test_extract_pdf_text_returns_content(tmp_path):
    """extract_pdf_text should return text content from a PDF."""
    from src.extractors import extract_pdf_text
    pdf_path = tmp_path / "test.pdf"
    _create_test_pdf(pdf_path, "Invoice #2026-001\nAmount: $1,500.00")
    result = extract_pdf_text(pdf_path)
    assert "Invoice #2026-001" in result
    assert "$1,500.00" in result


def test_extract_pdf_text_returns_empty_on_missing_file(tmp_path):
    """extract_pdf_text should return empty string for nonexistent file."""
    from src.extractors import extract_pdf_text
    result = extract_pdf_text(tmp_path / "nonexistent.pdf")
    assert result == ""


def test_extract_pdf_text_returns_empty_on_corrupt_file(tmp_path):
    """extract_pdf_text should return empty string for corrupt/invalid PDF."""
    from src.extractors import extract_pdf_text
    bad_pdf = tmp_path / "corrupt.pdf"
    bad_pdf.write_bytes(b"this is not a pdf")
    result = extract_pdf_text(bad_pdf)
    assert result == ""


def test_extract_pdf_text_truncates_long_content(tmp_path):
    """extract_pdf_text should truncate content exceeding max_chars."""
    from src.extractors import extract_pdf_text
    import pymupdf
    pdf_path = tmp_path / "long.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    # Write many short lines to guarantee extracted text exceeds max_chars
    for i in range(50):
        page.insert_text((72, 72 + i * 14), f"Line {i}: Some content here for padding.")
    doc.save(str(pdf_path))
    doc.close()
    result = extract_pdf_text(pdf_path, max_chars=100)
    assert len(result) <= 115  # 100 + room for "[truncated]"
    assert "[truncated]" in result
