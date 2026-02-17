# Skill: File Content Extraction

## Description
Extract text content from PDFs and generate descriptions of images dropped into the vault, creating enriched action files for Claude to process.

## Trigger
- File Watcher detects a new file in `vault/Incoming_Files/`

## Supported File Types

### PDF Files (.pdf)
- Extract text using PyMuPDF
- Truncate to 10,000 characters with `[truncated]` marker
- Handles corrupted/unreadable PDFs gracefully

### Image Files (.png, .jpg, .jpeg, .gif, .bmp, .tiff, .webp)
- Send to Claude CLI with `--image` flag for vision description
- Returns natural language description of image content
- Handles missing/corrupt files gracefully

## Process
1. Detect new file in `vault/Incoming_Files/`
2. Determine file type by extension
3. Extract content (PDF text) or generate description (image vision)
4. Create enriched action file in `vault/Needs_Action/`
5. Move original file to `vault/Incoming_Files/.processed/`

## Output
A markdown file in `vault/Needs_Action/` with:
```yaml
---
type: file
filename: document.pdf
extension: .pdf
detected_at: 2026-02-17T10:00:00Z
size_bytes: 12345
extracted: true
---

## Extracted Content
[PDF text or image description]

## Suggested Actions
- [ ] Review extracted content
- [ ] Process according to content type
```

## Configuration
- `FILE_WATCH_ENABLED=true` in `.env`
- `FILE_WATCH_DRY_RUN=true` for testing (detects but doesn't create action files)

## Implementation
- Module: `src/extractors.py` → `extract_pdf_text()`, `extract_image_description()`
- Watcher: `src/watchers/file_watcher.py`
