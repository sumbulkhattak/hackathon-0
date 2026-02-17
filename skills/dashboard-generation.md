# Skill: Dashboard Generation

## Description
Auto-generate Dashboard.md in the Obsidian vault with real-time system status, vault overview, pending approvals, and recent activity.

## Trigger
- After every processing cycle in main loop
- Every 5 seconds in dashboard-only mode

## Output: vault/Dashboard.md
```markdown
---
updated: 2026-02-17T10:30:00Z
---

# Digital FTE Dashboard

## System Status
**Status:** Active | Items to process: 3

## Vault Overview
| Folder | Items |
|--------|-------|
| Inbox | 0 |
| Needs_Action | 2 |
| Pending_Approval | 1 |
| ...    | ...   |

## Pending Approvals
- plan-invoice-reply.md (created: 2026-02-17)

## Recent Activity
- [2026-02-17 10:30] email_sent: reply to client@example.com
```

## Web Dashboard
Also accessible via browser at `http://localhost:{WEB_PORT}` (default 8000):
- Real-time folder counts
- Approve/reject buttons for pending items
- Activity log viewer
- REST API: `/api/status`, `/api/pending`, `/api/activity`

## Implementation
- Module: `src/dashboard.py` → `generate_dashboard()`, `update_dashboard()`
- Web: `src/web.py` → FastAPI endpoints
