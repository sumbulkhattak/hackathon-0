"""File content extractors for PDFs and images."""
import logging
import subprocess
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


def extract_image_description(
    path: Path,
    claude_model: str = "claude-sonnet-4-5-20250929",
    max_chars: int = MAX_EXTRACT_CHARS,
) -> str:
    """Extract a description of an image using Claude CLI vision.

    Returns empty string if extraction fails (missing file, CLI error, timeout).
    """
    if not path.exists():
        return ""
    prompt = (
        "Describe this image concisely. "
        "Extract any visible text, numbers, dates, and key details. "
        "Focus on factual content, not aesthetics."
    )
    try:
        result = subprocess.run(
            ["claude", "--print", "--model", claude_model, "--image", str(path), prompt],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            text = result.stdout.strip()
            if len(text) > max_chars:
                text = text[:max_chars] + "\n[truncated]"
            return text
        else:
            logger.warning(f"Claude vision failed for {path.name}: {result.stderr}")
            return ""
    except FileNotFoundError:
        logger.warning("Claude CLI not found for image extraction")
        return ""
    except subprocess.TimeoutExpired:
        logger.warning(f"Claude vision timed out for {path.name}")
        return ""
