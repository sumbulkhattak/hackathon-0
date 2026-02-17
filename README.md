# Digital FTE — Obsidian Tier

> Your life and business on autopilot. Local-first, agent-driven, human-in-the-loop. Now with web dashboard and smart email prioritization.

An autonomous AI agent that monitors your Gmail, drafts replies using Claude, and sends them after human approval — all powered by an Obsidian vault with a real-time web dashboard.

## Architecture

```
Gmail ──► Gmail Watcher ──► classify_priority() ──► vault/Needs_Action/
                              (keywords / VIP / newsletter)    (tagged: high|normal|low)
                                       │
Files ──► File Watcher ──► Extract ──┘
               (PDF text / image vision)
                                       │
                               Orchestrator + Claude ◄── vault/Agent_Memory.md
                               (processes high-priority first)
                                       │
                               confidence >= threshold?
                                  │           │
                                 YES          NO
                                  │           │
                             Auto-execute   vault/Pending_Approval/
                                  │           │
                                  │      Human reviews (Web UI or Obsidian)
                                  │        │      │
                                  │  Approved/  Rejected/
                                  │      │          │
                                  │  Gmail Reply  Claude reviews
                                  │      │          │
                                Done/  Done/   learning → Agent_Memory.md
                                                    │
                                              ┌─────┘
                                              ▼
                                   Dashboard.md (auto-updated)
                                   Web Dashboard (localhost:8000)
```

**Five layers:**
1. **Perception** — Gmail Watcher polls for new emails and classifies priority (high/normal/low); File Watcher extracts content from PDFs and images
2. **Reasoning** — Claude Code analyzes emails and generates plans
3. **Action** — High-confidence plans auto-execute; others require approval; rejected plans generate learnings
4. **Memory** — Obsidian vault stores everything as markdown; Dashboard.md auto-updates
5. **Interface** — Web dashboard at localhost:8000 for real-time monitoring and approval

## Prerequisites

- Python 3.13+
- Claude Code (Pro subscription)
- Obsidian v1.10.6+
- Google Cloud project with Gmail API enabled

## Gmail API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable the **Gmail API**: APIs & Services → Library → Search "Gmail API" → Enable
4. Create OAuth 2.0 credentials:
   - APIs & Services → Credentials → Create Credentials → OAuth Client ID
   - Application type: **Desktop app**
   - Download the JSON file
5. Save the file as `credentials/client_secret.json`

## Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd hackathon-0

# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env
# Edit .env with your preferences

# Initialize the Obsidian vault
python setup_vault.py
```

## Usage

```bash
# Start the Digital FTE (full mode with Gmail)
python main.py

# Start in dashboard-only mode (no Gmail credentials required)
python main.py --dashboard-only
```

### Web Dashboard

The web dashboard starts automatically at **http://localhost:8000** and provides:
- Real-time vault overview with folder counts
- Pending approvals queue with **Approve/Reject buttons**
- Needs Action items with priority indicators
- Recent activity log
- File viewer for any vault item
- REST API endpoints (`/api/status`, `/api/pending`, `/api/activity`)

### Full Mode

The agent will:
1. Poll Gmail every 60 seconds (configurable)
2. **Classify email priority** (high for urgent keywords/VIP senders, low for newsletters, normal otherwise)
3. Create action files in `vault/Needs_Action/` with priority tags
4. Detect files in `vault/Incoming_Files/`, extract text (PDFs) or descriptions (images), create enriched action files
5. **Process high-priority items first**, then normal, then low
6. Process them with Claude, which includes a confidence score in each plan
7. **Auto-approve high-confidence plans** (confidence >= threshold) and execute immediately
8. Route lower-confidence plans to `vault/Pending_Approval/` for human review
9. **Send email replies** for approved plans that include a reply draft
10. Archive to `vault/Done/`
11. **Learn from rejections** — analyze rejected plans and store learnings in Agent Memory
12. **Update Dashboard.md** after every processing cycle

Open the `vault/` folder in Obsidian to see your dashboard, or visit http://localhost:8000 for the web interface.

## Configuration

Edit `.env` to customize:

| Variable | Default | Description |
|----------|---------|-------------|
| `VAULT_PATH` | `./vault` | Path to Obsidian vault |
| `GMAIL_CHECK_INTERVAL` | `60` | Seconds between Gmail checks |
| `GMAIL_FILTER` | `is:unread` | Gmail search filter |
| `CLAUDE_MODEL` | `claude-sonnet-4-5-20250929` | Claude model for analysis |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `DAILY_SEND_LIMIT` | `20` | Max emails sent per day |
| `AUTO_APPROVE_THRESHOLD` | `1.0` | Confidence threshold for auto-approve (1.0 = disabled) |
| `VIP_SENDERS` | *(empty)* | Comma-separated emails that always get high priority |
| `WEB_ENABLED` | `true` | Enable web dashboard |
| `WEB_PORT` | `8000` | Web dashboard port |

## Vault Structure

```
vault/
├── Inbox/              # General inbox folder
├── Incoming_Files/     # Drop PDFs/images here for extraction
├── Needs_Action/       # New items detected by watchers
├── Plans/              # Claude-generated plans
├── Pending_Approval/   # Awaiting human review
├── Approved/           # Human-approved actions
├── Rejected/           # Human-rejected plans for review
├── Done/               # Completed items
├── Logs/               # Daily JSON activity logs
├── Dashboard.md        # Auto-generated system status
├── Agent_Memory.md     # Learnings from rejected plans
└── Company_Handbook.md # Rules for Claude's behavior
```

## Security

- Credentials stored in `credentials/` (gitignored)
- All secrets in `.env` (gitignored)
- Human-in-the-loop: email replies require approval unless auto-approve is enabled
- Daily send limit (default: 20) prevents runaway sends
- Activity logged to `vault/Logs/`

## Tier Declaration

**Obsidian Tier** — Gmail watcher with reply sending, smart email prioritization (urgency keywords, VIP senders, newsletter detection), file watcher with PDF text extraction and image vision, self-review loops, confidence-based auto-approve, web dashboard with real-time monitoring and approval UI, Obsidian vault with approval pipeline, auto-generated Dashboard.md.

## License

MIT
