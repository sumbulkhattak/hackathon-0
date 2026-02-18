"""Platinum Demo Gate — End-to-end simulation of the cloud/local split flow.

Demonstrates the minimum passing gate for Platinum tier:
1. Email arrives while Local is offline
2. Cloud drafts reply + writes approval file
3. When Local returns, user approves via web dashboard
4. Local executes send via MCP
5. Logs the action
6. Moves task to /Done

Usage:
    python demo_platinum.py              # Run full demo (auto-approve mode)
    python demo_platinum.py --manual     # Run demo with manual web approval
"""
import json
import shutil
import sys
import time
import threading
from datetime import datetime, timezone
from pathlib import Path

from src.config import load_config
from src.dashboard import update_dashboard
from src.utils import log_action
from src.vault_sync import write_update, merge_updates
from setup_vault import setup_vault


DEMO_EMAIL = {
    "id": "demo_platinum_001",
    "from": "client@example.com",
    "subject": "January Invoice Request",
    "date": datetime.now(timezone.utc).isoformat(),
    "body": "Hi, could you please send me the invoice for January? Thanks!",
    "priority": "high",
}

DEMO_PLAN = """\
## Analysis
Client is requesting their January invoice. This is a routine business request
from a known contact. The appropriate response is to acknowledge the request
and confirm that the invoice will be sent.

## Recommended Actions
1. Send a polite reply confirming invoice will be sent
2. Flag for local zone to generate and attach the actual invoice

## Requires Approval
- [x] Send email reply (requires Local approval)

## Reply Draft
---BEGIN REPLY---
Hi,

Thank you for reaching out. I've noted your request for the January invoice.
Our team will prepare and send it to you shortly.

Best regards
---END REPLY---

## Confidence
0.92
"""


def step(num, title):
    """Print a formatted step header."""
    print(f"\n{'='*60}")
    print(f"  STEP {num}: {title}")
    print(f"{'='*60}\n")


def run_demo(manual_approve: bool = False):
    """Run the full Platinum demo gate flow."""
    cfg = load_config()
    vault = cfg.vault_path
    setup_vault(vault)

    print("\n" + "=" * 60)
    print("  PLATINUM DEMO GATE — Cloud/Local Split Flow")
    print("=" * 60)
    print(f"\nVault: {vault}")
    print(f"Manual approve: {manual_approve}")

    # ─────────────────────────────────────────────────────────
    # STEP 1: Email arrives (simulated) — Cloud zone detects it
    # ─────────────────────────────────────────────────────────
    step(1, "EMAIL ARRIVES — Cloud watcher detects new email")

    email_file = vault / "Needs_Action" / "email" / f"email-january-invoice-{DEMO_EMAIL['id'][:8]}.md"
    email_file.parent.mkdir(parents=True, exist_ok=True)
    email_content = f"""---
type: email
from: {DEMO_EMAIL['from']}
subject: {DEMO_EMAIL['subject']}
date: {DEMO_EMAIL['date']}
priority: {DEMO_EMAIL['priority']}
gmail_id: {DEMO_EMAIL['id']}
---

# New Email: {DEMO_EMAIL['subject']}

**From:** {DEMO_EMAIL['from']}
**Date:** {DEMO_EMAIL['date']}
**Priority:** {DEMO_EMAIL['priority']}

## Body
{DEMO_EMAIL['body']}

## Suggested Actions
- [ ] Reply
- [ ] Forward
- [ ] Archive
"""
    email_file.write_text(email_content, encoding="utf-8")
    print(f"  Created: {email_file.relative_to(vault)}")

    log_action(
        logs_dir=vault / "Logs",
        actor="cloud_watcher",
        action="email_detected",
        source=DEMO_EMAIL["id"],
        result=f"action_file_created:{email_file.name}:priority={DEMO_EMAIL['priority']}",
    )
    print("  Logged: email_detected")
    time.sleep(0.5)

    # ─────────────────────────────────────────────────────────
    # STEP 2: Cloud zone drafts reply (Claude processes action)
    # ─────────────────────────────────────────────────────────
    step(2, "CLOUD DRAFTS REPLY — Claude creates plan in Pending_Approval")

    now = datetime.now(timezone.utc).isoformat()
    plan_name = email_file.name.replace("email-", "plan-")
    plan_path = vault / "Pending_Approval" / "email" / plan_name
    plan_path.parent.mkdir(parents=True, exist_ok=True)

    plan_content = f"""---
source: {email_file.name}
created: {now}
status: pending_approval
confidence: 0.92
action: reply
gmail_id: {DEMO_EMAIL['id']}
to: {DEMO_EMAIL['from']}
subject: "Re: {DEMO_EMAIL['subject']}"
---

# Plan: {email_file.stem}

{DEMO_PLAN}
"""
    plan_path.write_text(plan_content, encoding="utf-8")
    # Remove original action file (cloud processed it)
    email_file.unlink()
    print(f"  Created plan: {plan_path.relative_to(vault)}")
    print(f"  Removed action: {email_file.relative_to(vault)}")

    log_action(
        logs_dir=vault / "Logs",
        actor="cloud_orchestrator",
        action="plan_created",
        source=email_file.name,
        result=f"pending_approval:{plan_name}",
    )

    # Cloud writes update signal (single-writer rule: cloud never writes Dashboard.md)
    update_ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    write_update(
        vault,
        f"cloud-draft-{update_ts}.md",
        f"Cloud drafted reply plan for: {DEMO_EMAIL['subject']} (confidence: 0.92)",
    )
    print("  Cloud wrote update signal to Updates/")
    time.sleep(0.5)

    # ─────────────────────────────────────────────────────────
    # STEP 3: Local zone comes online — merges updates, sees pending approval
    # ─────────────────────────────────────────────────────────
    step(3, "LOCAL COMES ONLINE — Merges updates, sees pending approval")

    merged = merge_updates(vault)
    print(f"  Merged {merged} update(s) into Dashboard.md")

    update_dashboard(vault)
    print("  Dashboard.md updated with current vault state")

    # Show what's pending
    pending = list((vault / "Pending_Approval").rglob("*.md"))
    print(f"  Pending approvals: {len(pending)}")
    for p in pending:
        print(f"    - {p.relative_to(vault)}")

    # ─────────────────────────────────────────────────────────
    # STEP 4: User approves via web dashboard (or auto-approve)
    # ─────────────────────────────────────────────────────────
    step(4, "USER APPROVES — Local zone approves the draft")

    if manual_approve:
        # Start web dashboard for manual approval
        print("  Starting web dashboard at http://localhost:8000")
        print("  Please approve the pending item in the web UI, then press Enter...")

        import uvicorn
        from src.web import create_app, app
        create_app(vault)
        server_thread = threading.Thread(
            target=lambda: uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning"),
            daemon=True,
        )
        server_thread.start()
        time.sleep(2)
        print("\n  >>> Open http://localhost:8000 and click 'Approve' <<<")
        input("\n  Press Enter after approving... ")
    else:
        # Auto-approve: move from Pending_Approval to Approved
        approved_path = vault / "Approved" / "email" / plan_name
        approved_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(plan_path), str(approved_path))
        print(f"  Auto-approved: {plan_path.relative_to(vault)} -> Approved/email/{plan_name}")

        log_action(
            logs_dir=vault / "Logs",
            actor="local_user",
            action="approved",
            source=plan_name,
            result="moved_to_approved",
        )

    time.sleep(0.5)

    # ─────────────────────────────────────────────────────────
    # STEP 5: Local executes send via MCP (simulated)
    # ─────────────────────────────────────────────────────────
    step(5, "LOCAL EXECUTES SEND — Email MCP sends reply")

    # Find the approved file
    approved_files = list((vault / "Approved").rglob("*.md"))
    if not approved_files:
        print("  ERROR: No approved files found. Did you approve in the web UI?")
        return

    approved_file = approved_files[0]
    print(f"  Executing: {approved_file.relative_to(vault)}")
    print(f"  [SIMULATED] Sending reply to {DEMO_EMAIL['from']}...")
    print(f"  [SIMULATED] Subject: Re: {DEMO_EMAIL['subject']}")
    print(f"  [SIMULATED] Email sent successfully!")

    log_action(
        logs_dir=vault / "Logs",
        actor="local_orchestrator",
        action="email_sent",
        source=approved_file.name,
        result=f"reply_to:{DEMO_EMAIL['from']}",
    )
    time.sleep(0.5)

    # ─────────────────────────────────────────────────────────
    # STEP 6: Move to Done, update dashboard, log completion
    # ─────────────────────────────────────────────────────────
    step(6, "TASK COMPLETE — Moved to Done, dashboard updated")

    done_path = vault / "Done" / approved_file.name
    shutil.move(str(approved_file), str(done_path))
    print(f"  Moved to: Done/{done_path.name}")

    log_action(
        logs_dir=vault / "Logs",
        actor="local_orchestrator",
        action="executed",
        source=approved_file.name,
        result="moved_to_done",
    )

    update_dashboard(vault)
    print("  Dashboard.md updated")

    # ─────────────────────────────────────────────────────────
    # SUMMARY
    # ─────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  PLATINUM DEMO GATE — PASSED")
    print("=" * 60)
    print(f"""
  Flow completed successfully:
    1. Email arrived while Local was offline
    2. Cloud drafted reply + wrote approval file
    3. Cloud wrote update signal to Updates/
    4. Local came online, merged updates into Dashboard.md
    5. User approved the draft
    6. Local executed email send via MCP (simulated)
    7. Action logged to vault/Logs/
    8. Task moved to vault/Done/

  Vault state:
    - Needs_Action:      {len(list((vault / 'Needs_Action').rglob('*.md')))} items
    - Pending_Approval:  {len(list((vault / 'Pending_Approval').rglob('*.md')))} items
    - Approved:          {len(list((vault / 'Approved').rglob('*.md')))} items
    - Done:              {len(list((vault / 'Done').rglob('*.md')))} items

  Web dashboard: python main.py --dashboard-only
  View at: http://localhost:8000
""")


if __name__ == "__main__":
    manual = "--manual" in sys.argv
    run_demo(manual_approve=manual)
