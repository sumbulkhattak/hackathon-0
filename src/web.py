"""FastAPI web dashboard for Digital FTE — makes the system visible and demonstrable."""
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from src.dashboard import (
    OVERVIEW_FOLDERS,
    _count_files,
    _items_to_process,
    _pending_approvals,
    _recent_activity,
)
from src.utils import log_action, parse_frontmatter

app = FastAPI(title="Digital FTE Dashboard", version="1.0.0")

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

    # Pending approvals with metadata
    approvals = []
    pa_dir = vault / "Pending_Approval"
    if pa_dir.is_dir():
        for f in sorted(pa_dir.iterdir()):
            if f.is_file() and f.suffix == ".md":
                fm = parse_frontmatter(f)
                approvals.append({
                    "name": f.name,
                    "stem": f.stem,
                    "created": fm.get("created", "unknown"),
                    "confidence": fm.get("confidence", "N/A"),
                    "action": fm.get("action", "review"),
                    "source": fm.get("source", ""),
                })

    # Recent activity
    activity = _recent_activity(vault)
    activity.reverse()  # Most recent first

    # Needs_Action items
    needs_action = []
    na_dir = vault / "Needs_Action"
    if na_dir.is_dir():
        for f in sorted(na_dir.iterdir()):
            if f.is_file() and f.suffix == ".md":
                fm = parse_frontmatter(f)
                needs_action.append({
                    "name": f.name,
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

    html = _render_dashboard(
        status=status,
        status_color=status_color,
        total_active=total_active,
        folder_counts=folder_counts,
        approvals=approvals,
        needs_action=needs_action,
        activity=activity,
        done_items=done_items,
    )
    return HTMLResponse(content=html)


@app.get("/api/status")
async def api_status():
    """JSON API — vault status overview."""
    vault = _get_vault()
    counts = {f: _count_files(vault / f) for f in OVERVIEW_FOLDERS}
    total_active = _items_to_process(vault)
    return {
        "status": "active" if total_active > 0 else "idle",
        "items_to_process": total_active,
        "folders": counts,
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


@app.post("/approve/{filename}")
async def approve_action(filename: str):
    """Move a file from Pending_Approval to Approved."""
    vault = _get_vault()
    src = vault / "Pending_Approval" / filename
    if not src.exists():
        return {"error": f"File not found: {filename}"}
    dest = vault / "Approved" / filename
    shutil.move(str(src), str(dest))
    log_action(
        logs_dir=vault / "Logs",
        actor="web_dashboard",
        action="approved",
        source=filename,
        result="moved_to_approved",
    )
    return RedirectResponse(url="/", status_code=303)


@app.post("/reject/{filename}")
async def reject_action(filename: str):
    """Move a file from Pending_Approval to Rejected."""
    vault = _get_vault()
    src = vault / "Pending_Approval" / filename
    if not src.exists():
        return {"error": f"File not found: {filename}"}
    dest = vault / "Rejected" / filename
    shutil.move(str(src), str(dest))
    log_action(
        logs_dir=vault / "Logs",
        actor="web_dashboard",
        action="rejected",
        source=filename,
        result="moved_to_rejected",
    )
    return RedirectResponse(url="/", status_code=303)


@app.get("/view/{folder}/{filename}", response_class=HTMLResponse)
async def view_file(folder: str, filename: str):
    """View a file's content."""
    vault = _get_vault()
    file_path = vault / folder / filename
    if not file_path.exists():
        return HTMLResponse(content="<h1>File not found</h1>", status_code=404)
    content = file_path.read_text(encoding="utf-8")
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{filename} — Digital FTE</title>
<style>{_css()}</style>
</head>
<body>
<div class="container">
<a href="/" class="back-link">← Back to Dashboard</a>
<h1>{filename}</h1>
<p class="breadcrumb">{folder} / {filename}</p>
<pre class="file-content">{content}</pre>
</div>
</body>
</html>"""
    return HTMLResponse(content=html)


def _css() -> str:
    """Return the dashboard CSS."""
    return """
:root {
    --bg: #0f172a;
    --surface: #1e293b;
    --surface-hover: #334155;
    --border: #334155;
    --text: #e2e8f0;
    --text-muted: #94a3b8;
    --accent: #3b82f6;
    --green: #22c55e;
    --red: #ef4444;
    --yellow: #eab308;
    --orange: #f97316;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
}
.container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
h1 { font-size: 1.75rem; margin-bottom: 0.5rem; }
h2 { font-size: 1.25rem; margin-bottom: 0.75rem; color: var(--text-muted); }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; }
.header-title { display: flex; align-items: center; gap: 0.75rem; }
.status-badge {
    display: inline-flex; align-items: center; gap: 0.5rem;
    padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.875rem; font-weight: 600;
}
.status-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }
.card {
    background: var(--surface); border: 1px solid var(--border); border-radius: 0.75rem;
    padding: 1.25rem; transition: border-color 0.2s;
}
.card:hover { border-color: var(--accent); }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.folder-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; }
.folder-item {
    background: var(--bg); border-radius: 0.5rem; padding: 0.75rem;
    text-align: center;
}
.folder-count { font-size: 1.5rem; font-weight: 700; color: var(--accent); }
.folder-name { font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem; }
.approval-item {
    background: var(--bg); border-radius: 0.5rem; padding: 1rem;
    margin-bottom: 0.75rem; display: flex; justify-content: space-between; align-items: center;
}
.approval-info { flex: 1; }
.approval-name { font-weight: 600; font-size: 0.9rem; }
.approval-meta { font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem; }
.approval-actions { display: flex; gap: 0.5rem; }
.btn {
    padding: 0.375rem 0.75rem; border: none; border-radius: 0.375rem;
    font-size: 0.8rem; font-weight: 600; cursor: pointer; transition: opacity 0.2s;
}
.btn:hover { opacity: 0.85; }
.btn-approve { background: var(--green); color: #000; }
.btn-reject { background: var(--red); color: #fff; }
.btn-view { background: var(--surface-hover); color: var(--text); }
.activity-item {
    padding: 0.5rem 0; border-bottom: 1px solid var(--border);
    font-size: 0.85rem; display: flex; gap: 0.75rem;
}
.activity-item:last-child { border-bottom: none; }
.activity-time { color: var(--text-muted); white-space: nowrap; font-family: monospace; font-size: 0.8rem; }
.activity-action { color: var(--accent); font-weight: 500; }
.priority-high { color: var(--red); }
.priority-normal { color: var(--yellow); }
.priority-low { color: var(--text-muted); }
.empty-state { color: var(--text-muted); font-style: italic; padding: 1rem 0; text-align: center; }
.back-link { color: var(--accent); text-decoration: none; display: inline-block; margin-bottom: 1rem; }
.breadcrumb { color: var(--text-muted); font-size: 0.85rem; margin-bottom: 1rem; }
.file-content {
    background: var(--surface); border: 1px solid var(--border); border-radius: 0.5rem;
    padding: 1.25rem; white-space: pre-wrap; word-wrap: break-word; font-size: 0.85rem;
    line-height: 1.7; max-height: 70vh; overflow-y: auto;
}
.needs-action-item {
    background: var(--bg); border-radius: 0.5rem; padding: 0.75rem;
    margin-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: center;
}
.timestamp { color: var(--text-muted); font-size: 0.75rem; }
"""


def _render_dashboard(
    status: str,
    status_color: str,
    total_active: int,
    folder_counts: list[dict],
    approvals: list[dict],
    needs_action: list[dict],
    activity: list[dict],
    done_items: list[dict],
) -> str:
    """Render the HTML dashboard."""
    # Folder cards
    folder_html = ""
    for fc in folder_counts:
        count_color = "var(--accent)" if fc["count"] > 0 else "var(--text-muted)"
        folder_html += f"""
        <div class="folder-item">
            <div class="folder-count" style="color: {count_color}">{fc['count']}</div>
            <div class="folder-name">{fc['name']}</div>
        </div>"""

    # Pending approvals
    if approvals:
        approvals_html = ""
        for a in approvals:
            approvals_html += f"""
            <div class="approval-item">
                <div class="approval-info">
                    <div class="approval-name">{a['name']}</div>
                    <div class="approval-meta">
                        Source: {a['source']} | Confidence: {a['confidence']} | Action: {a['action']}
                    </div>
                </div>
                <div class="approval-actions">
                    <a href="/view/Pending_Approval/{a['name']}" class="btn btn-view">View</a>
                    <form method="post" action="/approve/{a['name']}" style="display:inline">
                        <button class="btn btn-approve" type="submit">Approve</button>
                    </form>
                    <form method="post" action="/reject/{a['name']}" style="display:inline">
                        <button class="btn btn-reject" type="submit">Reject</button>
                    </form>
                </div>
            </div>"""
    else:
        approvals_html = '<div class="empty-state">No pending approvals</div>'

    # Needs Action items
    if needs_action:
        na_html = ""
        for item in needs_action:
            priority_class = f"priority-{item['priority']}"
            na_html += f"""
            <div class="needs-action-item">
                <div>
                    <span class="{priority_class}" style="font-weight:700">●</span>
                    <a href="/view/Needs_Action/{item['name']}" style="color:var(--text);text-decoration:none">{item['subject']}</a>
                </div>
                <span class="timestamp">{item['type']} | {item['priority']}</span>
            </div>"""
    else:
        na_html = '<div class="empty-state">No action items</div>'

    # Recent activity
    if activity:
        activity_html = ""
        for entry in activity:
            ts = entry.get("timestamp", "")
            short_ts = ts[:16].replace("T", " ") if len(ts) >= 16 else ts
            action = entry.get("action", "unknown")
            result = entry.get("result", "")
            source = entry.get("source", "")
            activity_html += f"""
            <div class="activity-item">
                <span class="activity-time">{short_ts}</span>
                <span class="activity-action">{action}</span>
                <span>{source} → {result}</span>
            </div>"""
    else:
        activity_html = '<div class="empty-state">No recent activity</div>'

    # Done items
    if done_items:
        done_html = ""
        for item in done_items:
            done_html += f"""
            <div class="needs-action-item">
                <a href="/view/Done/{item['name']}" style="color:var(--text);text-decoration:none">{item['name']}</a>
            </div>"""
    else:
        done_html = '<div class="empty-state">No completed items yet</div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Digital FTE — Dashboard</title>
<style>{_css()}</style>
</head>
<body>
<div class="container">
    <div class="header">
        <div class="header-title">
            <h1>Digital FTE Dashboard</h1>
            <span class="status-badge" style="background: {status_color}20; color: {status_color}">
                <span class="status-dot" style="background: {status_color}"></span>
                {status}
            </span>
        </div>
        <div class="timestamp">Items to process: {total_active}</div>
    </div>

    <div class="grid">
        <div class="card">
            <div class="card-header"><h2>Vault Overview</h2></div>
            <div class="folder-grid">
                {folder_html}
            </div>
        </div>

        <div class="card">
            <div class="card-header"><h2>Pending Approvals</h2></div>
            {approvals_html}
        </div>
    </div>

    <div class="grid">
        <div class="card">
            <div class="card-header"><h2>Needs Action</h2></div>
            {na_html}
        </div>

        <div class="card">
            <div class="card-header"><h2>Recent Activity</h2></div>
            {activity_html}
        </div>
    </div>

    <div class="card" style="margin-bottom: 2rem">
        <div class="card-header"><h2>Completed (Recent)</h2></div>
        {done_html}
    </div>

    <div style="text-align:center; color:var(--text-muted); font-size:0.8rem; padding:1rem 0">
        Digital FTE — Obsidian Tier | Auto-refreshes on page load |
        <a href="/api/status" style="color:var(--accent)">API: /api/status</a> |
        <a href="/api/pending" style="color:var(--accent)">API: /api/pending</a> |
        <a href="/api/activity" style="color:var(--accent)">API: /api/activity</a>
    </div>
</div>
</body>
</html>"""
