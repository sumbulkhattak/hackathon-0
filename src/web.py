"""FastAPI web dashboard for Digital FTE — makes the system visible and demonstrable."""
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.dashboard import (
    OVERVIEW_FOLDERS,
    _count_files,
    _items_to_process,
    _pending_approvals,
    _recent_activity,
)
from src.utils import log_action, parse_frontmatter
from src.secrets_isolation import get_zone_capabilities

app = FastAPI(title="Digital FTE Dashboard", version="1.0.0")

# Resolve paths relative to project root
_project_root = Path(__file__).resolve().parent.parent
app.mount("/static", StaticFiles(directory=str(_project_root / "static")), name="static")
templates = Jinja2Templates(directory=str(_project_root / "templates"))

# Will be set by create_app()
_vault_path: Path | None = None


def create_app(vault_path: Path) -> FastAPI:
    """Configure the FastAPI app with vault path."""
    global _vault_path
    _vault_path = vault_path
    return app


def _get_vault() -> Path:
    """Return the configured vault path."""
    if _vault_path is None:
        raise RuntimeError("Vault path not configured. Call create_app() first.")
    return _vault_path


@app.get("/", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Main dashboard page — shows system status, vault overview, approvals, activity."""
    vault = _get_vault()
    total_active = _items_to_process(vault)
    status = "Active" if total_active > 0 else "Idle"
    status_color = "#22c55e" if total_active > 0 else "#6b7280"

    # Folder counts
    folder_counts = []
    for folder in OVERVIEW_FOLDERS:
        count = _count_files(vault / folder)
        folder_counts.append({"name": folder, "count": count})

    # Pending approvals with metadata (scan recursively for domain subdirs)
    approvals = []
    pa_dir = vault / "Pending_Approval"
    if pa_dir.is_dir():
        for f in sorted(pa_dir.rglob("*.md")):
            if f.is_file():
                fm = parse_frontmatter(f)
                # Build relative path for approve/reject routes
                rel = f.relative_to(pa_dir)
                approvals.append({
                    "name": f.name,
                    "rel_path": str(rel).replace("\\", "/"),
                    "stem": f.stem,
                    "domain": f.parent.name if f.parent != pa_dir else "",
                    "created": fm.get("created", "unknown"),
                    "confidence": fm.get("confidence", "N/A"),
                    "action": fm.get("action", "review"),
                    "source": fm.get("source", ""),
                })

    # Recent activity
    activity = _recent_activity(vault)
    activity.reverse()  # Most recent first

    # Needs_Action items (scan recursively for domain subdirs)
    needs_action = []
    na_dir = vault / "Needs_Action"
    if na_dir.is_dir():
        for f in sorted(na_dir.rglob("*.md")):
            if f.is_file():
                fm = parse_frontmatter(f)
                needs_action.append({
                    "name": f.name,
                    "domain": f.parent.name if f.parent != na_dir else "",
                    "priority": fm.get("priority", "normal"),
                    "type": fm.get("type", "unknown"),
                    "subject": fm.get("subject", f.stem),
                })

    # Done items (last 10)
    done_items = []
    done_dir = vault / "Done"
    if done_dir.is_dir():
        files = sorted(done_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        for f in files[:10]:
            if f.is_file() and f.suffix == ".md":
                done_items.append({"name": f.name})

    # Build summary counts for top-level cards
    fc_map = {fc["name"]: fc["count"] for fc in folder_counts}
    summary = {
        "needs_action": fc_map.get("Needs_Action", 0),
        "plans": fc_map.get("Plans", 0),
        "completed": fc_map.get("Done", 0),
    }

    return templates.TemplateResponse(request, "dashboard.html", {
        "status": status,
        "status_color": status_color,
        "total_active": total_active,
        "summary": summary,
        "folder_counts": folder_counts,
        "approvals": approvals,
        "needs_action": needs_action,
        "activity": activity,
        "done_items": done_items,
    })


@app.get("/health")
async def health_check():
    """Health endpoint for cloud monitoring and load balancers."""
    vault = _get_vault()
    work_zone = os.getenv("WORK_ZONE", "local")
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "vault_exists": vault.is_dir(),
        "work_zone": work_zone,
        "capabilities": get_zone_capabilities(work_zone),
    }


@app.get("/api/status")
async def api_status():
    """JSON API — vault status overview."""
    vault = _get_vault()
    counts = {f: _count_files(vault / f) for f in OVERVIEW_FOLDERS}
    total_active = _items_to_process(vault)
    work_zone = os.getenv("WORK_ZONE", "local")
    return {
        "status": "active" if total_active > 0 else "idle",
        "items_to_process": total_active,
        "folders": counts,
        "work_zone": work_zone,
    }


@app.get("/api/pending")
async def api_pending():
    """JSON API — list pending approval items."""
    vault = _get_vault()
    return {"approvals": _pending_approvals(vault)}


@app.get("/api/activity")
async def api_activity():
    """JSON API — recent activity log."""
    vault = _get_vault()
    entries = _recent_activity(vault)
    entries.reverse()
    return {"activity": entries}


@app.get("/tasks")
async def tasks_list():
    """JSON API — list current tasks from Needs_Action and Pending_Approval."""
    vault = _get_vault()
    tasks = []
    for folder in ["Needs_Action", "Pending_Approval"]:
        folder_dir = vault / folder
        if folder_dir.is_dir():
            for f in sorted(folder_dir.rglob("*.md")):
                if f.is_file():
                    fm = parse_frontmatter(f)
                    tasks.append({
                        "name": f.name,
                        "folder": folder,
                        "type": fm.get("type", "unknown"),
                        "priority": fm.get("priority", "normal"),
                        "subject": fm.get("subject", f.stem),
                    })
    return {"tasks": tasks}


@app.post("/approve/{filepath:path}")
async def approve_action(filepath: str):
    """Move a file from Pending_Approval to Approved (supports domain subdirs)."""
    vault = _get_vault()
    src = vault / "Pending_Approval" / filepath
    if not src.exists():
        return {"error": f"File not found: {filepath}"}
    dest = vault / "Approved" / filepath
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dest))
    log_action(
        logs_dir=vault / "Logs",
        actor="web_dashboard",
        action="approved",
        source=filepath,
        result="moved_to_approved",
    )
    return RedirectResponse(url="/", status_code=303)


@app.post("/reject/{filepath:path}")
async def reject_action(filepath: str):
    """Move a file from Pending_Approval to Rejected (supports domain subdirs)."""
    vault = _get_vault()
    src = vault / "Pending_Approval" / filepath
    if not src.exists():
        return {"error": f"File not found: {filepath}"}
    dest = vault / "Rejected" / filepath
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dest))
    log_action(
        logs_dir=vault / "Logs",
        actor="web_dashboard",
        action="rejected",
        source=filepath,
        result="moved_to_rejected",
    )
    return RedirectResponse(url="/", status_code=303)


@app.get("/view/{folder}/{filename}", response_class=HTMLResponse)
async def view_file(request: Request, folder: str, filename: str):
    """View a file's content."""
    vault = _get_vault()
    file_path = vault / folder / filename
    if not file_path.exists():
        return HTMLResponse(content="<h1>File not found</h1>", status_code=404)
    content = file_path.read_text(encoding="utf-8")
    return templates.TemplateResponse(request, "view.html", {
        "filename": filename,
        "folder": folder,
        "content": content,
    })
