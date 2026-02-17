# Digital FTE Diamond — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add file content extraction so PDFs and images dropped into `Incoming_Files/` produce action files with real extracted content that Claude can analyze.

**Architecture:** New `src/extractors.py` module with `extract_pdf_text()` (PyMuPDF) and `extract_image_description()` (Claude CLI vision). FileWatcher calls extractors in `create_action_file()` and embeds results. Orchestrator unchanged.

**Tech Stack:** Python 3.13, pymupdf, Claude CLI (subprocess), pytest

---

### Task 1: Add `pymupdf` dependency

**Files:**
- Modify: `requirements.txt`

**Step 1: Add pymupdf to requirements**

Add `pymupdf` to `requirements.txt` after the existing dependencies:

```
pymupdf==1.25.3
```

**Step 2: Install dependencies**

Run: `pip install pymupdf`
Expected: Successful installation

**Step 3: Verify import**

Run: `python -c "import pymupdf; print('pymupdf OK')"`
Expected: `pymupdf OK`

**Step 4: Commit**

```bash
git add requirements.txt
git commit -m "deps: add pymupdf for PDF text extraction"
```

---

### Task 2: Add `extract_pdf_text()` function

**Files:**
- Create: `tests/test_extractors.py`
- Create: `src/extractors.py`

**Step 1: Create a small test PDF fixture**

Create a helper in the test file that generates a real PDF using pymupdf:

```python
"""Tests for file content extractors."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


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
    pdf_path = tmp_path / "long.pdf"
    _create_test_pdf(pdf_path, "A" * 500)
    result = extract_pdf_text(pdf_path, max_chars=100)
    assert len(result) <= 115  # 100 + room for "[truncated]"
    assert "[truncated]" in result
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_extractors.py -k "extract_pdf" -v`
Expected: FAIL — `src.extractors` module not found

**Step 3: Implement `extract_pdf_text()`**

Create `src/extractors.py`:

```python
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
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_extractors.py -k "extract_pdf" -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/extractors.py tests/test_extractors.py
git commit -m "feat: add extract_pdf_text utility using PyMuPDF"
```

---

### Task 3: Add `extract_image_description()` function

**Files:**
- Modify: `tests/test_extractors.py`
- Modify: `src/extractors.py`

**Step 1: Write failing tests**

Add to `tests/test_extractors.py`:

```python
def test_extract_image_description_calls_claude(tmp_path):
    """extract_image_description should call Claude CLI with the image."""
    from src.extractors import extract_image_description
    img_path = tmp_path / "receipt.png"
    img_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)  # minimal PNG header
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Receipt from Store XYZ. Total: $42.50. Date: 2026-02-17."
        )
        result = extract_image_description(img_path)
    assert "Receipt" in result or "$42.50" in result
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert "claude" in call_args[0]


def test_extract_image_description_returns_empty_on_failure(tmp_path):
    """extract_image_description should return empty string when Claude fails."""
    from src.extractors import extract_image_description
    img_path = tmp_path / "photo.jpg"
    img_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)  # minimal JPEG header
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr="error")
        result = extract_image_description(img_path)
    assert result == ""


def test_extract_image_description_returns_empty_on_missing_file(tmp_path):
    """extract_image_description should return empty string for nonexistent file."""
    from src.extractors import extract_image_description
    result = extract_image_description(tmp_path / "ghost.png")
    assert result == ""


def test_extract_image_description_returns_empty_on_timeout(tmp_path):
    """extract_image_description should return empty string on subprocess timeout."""
    import subprocess
    from src.extractors import extract_image_description
    img_path = tmp_path / "slow.png"
    img_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=120)
        result = extract_image_description(img_path)
    assert result == ""
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_extractors.py -k "extract_image" -v`
Expected: FAIL — `extract_image_description` not found

**Step 3: Implement `extract_image_description()`**

Add to `src/extractors.py`:

```python
import subprocess


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
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_extractors.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/extractors.py tests/test_extractors.py
git commit -m "feat: add extract_image_description using Claude CLI vision"
```

---

### Task 4: Add `claude_model` parameter to FileWatcher

**Files:**
- Modify: `tests/watchers/test_file_watcher.py`
- Modify: `src/watchers/file_watcher.py`

**Step 1: Write failing tests**

Add to `tests/watchers/test_file_watcher.py`:

```python
def test_file_watcher_accepts_claude_model(vault):
    """FileWatcher should accept and store claude_model parameter."""
    watcher = FileWatcher(vault_path=vault, claude_model="claude-opus-4-6")
    assert watcher.claude_model == "claude-opus-4-6"


def test_file_watcher_claude_model_default(vault):
    """FileWatcher should default claude_model to claude-sonnet-4-5-20250929."""
    watcher = FileWatcher(vault_path=vault)
    assert watcher.claude_model == "claude-sonnet-4-5-20250929"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/watchers/test_file_watcher.py -k "claude_model" -v`
Expected: FAIL — `__init__` has no `claude_model` parameter

**Step 3: Update FileWatcher `__init__`**

In `src/watchers/file_watcher.py`, change:

```python
    def __init__(self, vault_path: Path, check_interval: int = 30, dry_run: bool = False):
```

To:

```python
    def __init__(self, vault_path: Path, check_interval: int = 30, dry_run: bool = False,
                 claude_model: str = "claude-sonnet-4-5-20250929"):
```

Add inside `__init__` after `self.dry_run = dry_run`:

```python
        self.claude_model = claude_model
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/watchers/test_file_watcher.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/watchers/file_watcher.py tests/watchers/test_file_watcher.py
git commit -m "feat: add claude_model parameter to FileWatcher"
```

---

### Task 5: Integrate extractors into `create_action_file()`

**Files:**
- Modify: `tests/watchers/test_file_watcher.py`
- Modify: `src/watchers/file_watcher.py`

**Step 1: Write failing tests**

Add to `tests/watchers/test_file_watcher.py`:

```python
from unittest.mock import patch, MagicMock


def test_action_file_contains_extracted_pdf_text(vault):
    """create_action_file should embed extracted PDF text in the action file."""
    watcher = FileWatcher(vault_path=vault)
    _drop_file(vault, "invoice.pdf")
    items = watcher.check_for_updates()
    with patch("src.watchers.file_watcher.extract_pdf_text") as mock_extract:
        mock_extract.return_value = "Invoice #99\nAmount: $500.00"
        path = watcher.create_action_file(items[0])
    content = path.read_text()
    assert "## Extracted Content" in content
    assert "Invoice #99" in content
    assert "$500.00" in content
    assert "extracted: true" in content


def test_action_file_contains_extracted_image_description(vault):
    """create_action_file should embed Claude vision description for images."""
    watcher = FileWatcher(vault_path=vault)
    _drop_file(vault, "receipt.png")
    items = watcher.check_for_updates()
    with patch("src.watchers.file_watcher.extract_image_description") as mock_extract:
        mock_extract.return_value = "Receipt from Store XYZ. Total: $42.50."
        path = watcher.create_action_file(items[0])
    content = path.read_text()
    assert "## Extracted Content" in content
    assert "Receipt from Store XYZ" in content
    assert "extracted: true" in content


def test_action_file_falls_back_on_extraction_failure(vault):
    """create_action_file should use placeholder when extraction returns empty."""
    watcher = FileWatcher(vault_path=vault)
    _drop_file(vault, "broken.pdf")
    items = watcher.check_for_updates()
    with patch("src.watchers.file_watcher.extract_pdf_text") as mock_extract:
        mock_extract.return_value = ""
        path = watcher.create_action_file(items[0])
    content = path.read_text()
    assert "extracted: false" in content
    assert "pending" in content.lower() or "Review manually" in content
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/watchers/test_file_watcher.py -k "extracted" -v`
Expected: FAIL — no `## Extracted Content` section, no `extracted:` frontmatter

**Step 3: Update `create_action_file()` in `src/watchers/file_watcher.py`**

Add import at top of file:

```python
from src.extractors import extract_pdf_text, extract_image_description
```

Define which extensions are images vs PDFs:

```python
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"}
```

Replace the `create_action_file` method body (after the dry_run check) with:

```python
    def create_action_file(self, item: dict) -> Path:
        """Generate a markdown task file in Needs_Action with extracted content."""
        if self.dry_run:
            logger.info(f"DRY-RUN: Would create action file for {item['filename']}")
            self._processed.add(item["filename"])
            return item["path"]

        # Extract content based on file type
        extracted_text = ""
        ext = item["extension"]
        if ext == ".pdf":
            extracted_text = extract_pdf_text(item["path"])
        elif ext in IMAGE_EXTENSIONS:
            extracted_text = extract_image_description(item["path"], self.claude_model)

        has_content = bool(extracted_text.strip())

        slug = slugify(item["filename"])[:50] or "file"
        filename = f"file-{slug}.md"
        path = self.needs_action_dir / filename

        if has_content:
            summary_section = f"## Extracted Content\n{extracted_text}"
        else:
            summary_section = "## Summary\nPending analysis — file content extraction not yet available. Review manually."

        content = f"""---
type: file
filename: {item['filename']}
extension: {item['extension']}
detected_at: {item['detected_at']}
size_bytes: {item['size_bytes']}
extracted: {str(has_content).lower()}
priority: normal
---

# New File: {item['filename']}

**Filename:** {item['filename']}
**Type:** {item['extension']}
**Detected:** {item['detected_at']}
**Size:** {item['size_bytes']} bytes

{summary_section}

## Suggested Actions
- [ ] Review file contents
- [ ] Categorize and file
- [ ] Forward to relevant party
- [ ] Archive
"""
        path.write_text(content, encoding="utf-8")
        logger.info(f"Created action file: {path.name} for {item['filename']} (extracted={has_content})")

        # Move original file out of Incoming_Files to prevent reprocessing
        processed_dir = self.vault_path / "Incoming_Files" / ".processed"
        processed_dir.mkdir(exist_ok=True)
        shutil.move(str(item["path"]), str(processed_dir / item["filename"]))

        self._processed.add(item["filename"])

        log_action(
            logs_dir=self.vault_path / "Logs",
            actor="file_watcher",
            action="file_detected",
            source=item["filename"],
            result=f"action_file_created:{filename}:extracted={has_content}",
        )
        return path
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/watchers/test_file_watcher.py -v`
Expected: ALL PASS

**Step 5: Run full suite**

Run: `pytest tests/ -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add src/watchers/file_watcher.py tests/watchers/test_file_watcher.py
git commit -m "feat: integrate file content extraction into FileWatcher"
```

---

### Task 6: Wire `claude_model` into FileWatcher in `main.py`

**Files:**
- Modify: `main.py`

**Step 1: Update FileWatcher construction in `main.py`**

Change:

```python
        file_watcher = FileWatcher(
            vault_path=cfg.vault_path,
            dry_run=cfg.file_watch_dry_run,
        )
```

To:

```python
        file_watcher = FileWatcher(
            vault_path=cfg.vault_path,
            dry_run=cfg.file_watch_dry_run,
            claude_model=cfg.claude_model,
        )
```

**Step 2: Run full test suite**

Run: `pytest tests/ -v`
Expected: ALL PASS

**Step 3: Commit**

```bash
git add main.py
git commit -m "feat: pass claude_model to FileWatcher in main entry point"
```

---

### Task 7: Add E2E integration test for file extraction pipeline

**Files:**
- Modify: `tests/test_integration.py`

**Step 1: Write the integration test**

Add to `tests/test_integration.py`:

```python
def test_file_extraction_pipeline(tmp_path):
    """End-to-end: PDF dropped -> extracted -> action file with content -> orchestrator processes."""
    from setup_vault import setup_vault
    from src.watchers.file_watcher import FileWatcher
    from src.orchestrator import Orchestrator

    setup_vault(tmp_path)

    # Create a real PDF with pymupdf
    import pymupdf
    pdf_path = tmp_path / "Incoming_Files" / "invoice-2026.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Invoice #2026-001\nAmount: $1,500.00\nDue: 2026-03-15")
    doc.save(str(pdf_path))
    doc.close()

    # Step 1: FileWatcher detects and extracts
    watcher = FileWatcher(vault_path=tmp_path)
    count = watcher.run_once()
    assert count == 1
    action_files = list((tmp_path / "Needs_Action").glob("*.md"))
    assert len(action_files) == 1

    # Verify extraction happened
    content = action_files[0].read_text()
    assert "## Extracted Content" in content
    assert "Invoice #2026-001" in content
    assert "$1,500.00" in content
    assert "extracted: true" in content

    # Step 2: Orchestrator processes the extracted file
    orch = Orchestrator(vault_path=tmp_path)
    with patch.object(orch, "_invoke_claude") as mock_claude:
        mock_claude.return_value = (
            "## Analysis\nInvoice for $1,500 due 2026-03-15.\n\n"
            "## Recommended Actions\n1. Schedule payment\n2. File invoice\n\n"
            "## Requires Approval\n- [ ] Schedule payment\n\n"
            "## Confidence\n0.7"
        )
        plan_path = orch.process_action(action_files[0])

    assert plan_path.parent.name == "Pending_Approval"
    plan_content = plan_path.read_text()
    assert "Invoice" in plan_content
```

**Step 2: Run integration tests**

Run: `pytest tests/test_integration.py -v`
Expected: ALL PASS

**Step 3: Run full suite**

Run: `pytest tests/ -v`
Expected: ALL PASS

**Step 4: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add E2E integration test for file extraction pipeline"
```

---

### Task 8: Update README for Diamond tier

**Files:**
- Modify: `README.md`

**Step 1: Update README**

1. Change title from `# Digital FTE — Platinum Tier` to `# Digital FTE — Diamond Tier`

2. Update tagline:
   > Your life and business on autopilot. Local-first, agent-driven, human-in-the-loop. Now with document content extraction.

3. Update architecture diagram — add extraction step after file watcher:
   ```
   Gmail ──► Gmail Watcher ──► vault/Needs_Action/
                                       │
   Files ──► File Watcher ──► Extract ──┘
                  (PDF text / image vision)
                                       │
                               Orchestrator + Claude ◄── vault/Agent_Memory.md
                                       │
                               confidence >= threshold?
                                  │           │
                                 YES          NO
                                  │           │
                             Auto-execute   vault/Pending_Approval/
                                  │           │
                                  │      Human reviews
                                  │        │      │
                                  │  Approved/  Rejected/
                                  │      │          │
                                  │  Gmail Reply  Claude reviews
                                  │      │          │
                                Done/  Done/   learning → Agent_Memory.md
                                                    │
                                                  Done/
   ```

4. Update layer 1:
   > 1. **Perception** — Gmail Watcher polls for new emails; File Watcher extracts content from PDFs and images

5. Update the usage list to include file extraction:
   After item 2, add:
   > 3. Detect files in `vault/Incoming_Files/`, extract text (PDFs) or descriptions (images), create enriched action files

6. Update tier declaration:
   > **Diamond Tier** — Gmail watcher with reply sending, file watcher with PDF text extraction and image vision, self-review loops, confidence-based auto-approve, Obsidian vault with approval pipeline.

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update README for Diamond tier with file extraction"
```

---

### Task 9: Final verification

**Step 1: Run the full test suite**

Run: `pytest tests/ -v`
Expected: ALL PASS

**Step 2: Verify imports**

Run: `python -c "from src.extractors import extract_pdf_text, extract_image_description; print('Extractors OK')"`
Expected: `Extractors OK`

**Step 3: Verify PDF extraction works end-to-end**

Run: `python -c "from pathlib import Path; import pymupdf; doc=pymupdf.open(); p=doc.new_page(); p.insert_text((72,72),'Hello Diamond'); doc.save('/tmp/test.pdf'); doc.close(); from src.extractors import extract_pdf_text; print(extract_pdf_text(Path('/tmp/test.pdf')))"`
Expected: Output containing `Hello Diamond`
