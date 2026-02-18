"""File system watcher — monitors Incoming_Files for PDFs and images."""
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

from src.extractors import extract_pdf_text, extract_image_description
from src.utils import log_action, slugify
from src.watchers.base_watcher import BaseWatcher

logger = logging.getLogger("digital_fte.file_watcher")

SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"}


class FileWatcher(BaseWatcher):
    def __init__(self, vault_path: Path, check_interval: int = 30, dry_run: bool = False,
                 claude_model: str = "claude-sonnet-4-5-20250929"):
        super().__init__(vault_path, check_interval, domain="file")
        self.incoming_dir = vault_path / "Incoming_Files"
        self.incoming_dir.mkdir(parents=True, exist_ok=True)
        self.dry_run = dry_run
        self.claude_model = claude_model
        self._processed: set[str] = set()

    def check_for_updates(self) -> list[dict]:
        """Scan Incoming_Files for new PDFs and images."""
        items = []
        if not self.incoming_dir.exists():
            return items

        for path in sorted(self.incoming_dir.iterdir()):
            if not path.is_file():
                continue
            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            if path.name in self._processed:
                continue

            now = datetime.now(timezone.utc).isoformat()
            item = {
                "filename": path.name,
                "extension": path.suffix.lower(),
                "path": path,
                "detected_at": now,
                "size_bytes": path.stat().st_size,
            }
            items.append(item)

            if self.dry_run:
                logger.info(f"DRY-RUN: Detected {path.name} ({path.suffix.lower()}, {path.stat().st_size} bytes)")

        if items and not self.dry_run:
            logger.info(f"Detected {len(items)} new file(s) in Incoming_Files")

        return items

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
            result=f"action_file_created:{filename}",
        )
        return path

    def run_once(self) -> int:
        """Override to support dry-run mode."""
        items = self.check_for_updates()
        if self.dry_run:
            for item in items:
                self._processed.add(item["filename"])
            return 0
        count = 0
        for item in items:
            try:
                self.create_action_file(item)
                count += 1
            except Exception as e:
                logger.error(f"Failed to process {item['filename']}: {e}")
        return count
