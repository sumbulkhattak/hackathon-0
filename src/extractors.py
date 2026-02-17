"""File content extractors for PDFs and images."""
import logging
from pathlib import Path

logger = logging.getLogger("digital_fte.extractors")

MAX_EXTRACT_CHARS = 10000


def extract_pdf_text(path: Path, max_chars: int = MAX_EXTRACT_CHARS) -> str:
    """Extract text content from a PDF file using PyMuPDF.

    Returns empty string if extraction fails (missing file, corrupt PDF, etc.).
    Truncates to max_chars with a '[truncated]' marker if content is too long.
    """
    try:
        import pymupdf
        doc = pymupdf.open(str(path))
        pages = []
        for page in doc:
            pages.append(page.get_text())
        doc.close()
        text = "\n".join(pages).strip()
        if len(text) > max_chars:
            text = text[:max_chars] + "\n[truncated]"
        return text
    except Exception as e:
        logger.warning(f"PDF extraction failed for {path.name}: {e}")
        return ""
