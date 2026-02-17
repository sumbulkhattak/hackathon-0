# Digital FTE Diamond — Design Document

**Goal:** Add file content extraction so PDFs and images dropped into `Incoming_Files/` are analyzed by Claude with real content instead of placeholders.

**Approach:** New `src/extractors.py` module. PyMuPDF for PDF text extraction, Claude CLI vision for image descriptions. FileWatcher calls extractors and embeds results in action files. Orchestrator unchanged.

---

## Architecture

```
Incoming_Files/
      │
  FileWatcher.create_action_file()
      │
      ├── .pdf → extract_pdf_text(path) → raw text
      │
      └── .png/.jpg/... → extract_image_description(path, claude_model) → description
      │
      ▼
  Action file includes extracted content in ## Extracted Content
      │
      ▼
  Orchestrator + Claude analyzes full content (handbook + memory + extracted text)
```

## Components

### 1. `extract_pdf_text(path: Path) -> str`
- Uses PyMuPDF (`pymupdf` package) to read all pages
- Returns concatenated text, stripped of excessive whitespace
- Returns empty string on failure (corrupt, encrypted, etc.)
- Truncates to 10,000 characters to prevent oversized action files

### 2. `extract_image_description(path: Path, claude_model: str) -> str`
- Reads image file, encodes as base64
- Calls Claude CLI via subprocess with the image for a description
- Prompt: "Describe this image concisely. Extract any visible text, numbers, dates, and key details."
- Returns empty string on failure (timeout, CLI not found)
- Timeout: 120 seconds

### 3. FileWatcher updates
- Constructor gains `claude_model: str` parameter (default: "claude-sonnet-4-5-20250929")
- `create_action_file()` calls appropriate extractor based on file extension
- Extracted content replaces placeholder in `## Summary` / `## Extracted Content`
- Frontmatter gains `extracted: true/false` field

### 4. Action file format (updated)

```markdown
---
type: file
filename: invoice-2026.pdf
extension: .pdf
detected_at: 2026-02-17T10:00:00Z
size_bytes: 45000
extracted: true
priority: normal
---

# New File: invoice-2026.pdf

**Filename:** invoice-2026.pdf
**Type:** .pdf
**Detected:** 2026-02-17T10:00:00Z
**Size:** 45000 bytes

## Extracted Content
Invoice #2026-001
Date: 2026-02-15
Amount: $1,500.00
Due: 2026-03-15
...

## Suggested Actions
- [ ] Review file contents
- [ ] Categorize and file
- [ ] Forward to relevant party
- [ ] Archive
```

## Config Changes
- No new environment variables needed
- `claude_model` already exists in config, passed to FileWatcher for image extraction

## Dependencies
- New: `pymupdf` (PyMuPDF) for PDF text extraction
- Existing: Claude CLI for image vision

## Error Handling
- PDF extraction failure → `extracted: false`, placeholder text retained
- Image extraction failure → `extracted: false`, placeholder text retained
- Oversized content → truncated to 10,000 characters with "[truncated]" marker
- All failures logged but never block the pipeline

## Testing Strategy
- Unit tests for `extract_pdf_text()` with real small PDF fixture
- Unit tests for `extract_image_description()` with mocked subprocess
- Unit tests for FileWatcher integration with extraction
- E2E integration test: file → extract → action file → orchestrator processes

## Out of Scope
- OCR for scanned PDFs (future enhancement)
- Structured data extraction (JSON schemas for invoices)
- Multi-file correlation (linking related documents)
- Document classification beyond what Claude infers
