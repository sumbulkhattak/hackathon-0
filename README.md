# Digital FTE — Platinum Tier

> Your life and business on autopilot. Local-first, agent-driven, human-in-the-loop. Now with confidence-based auto-approve.

An autonomous AI agent that monitors your Gmail, drafts replies using Claude, and sends them after human approval — all powered by an Obsidian vault.

## Architecture

```
Gmail ──► Gmail Watcher ──► vault/Needs_Action/
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

**Four layers:**
1. **Perception** — Gmail Watcher polls for new emails
2. **Reasoning** — Claude Code analyzes emails and generates plans
3. **Action** — High-confidence plans auto-execute; others require approval; rejected plans generate learnings
4. **Memory** — Obsidian vault stores everything as markdown

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
# Start the Digital FTE
python main.py
```

The agent will:
1. Poll Gmail every 60 seconds (configurable)
2. Create action files in `vault/Needs_Action/`
3. Process them with Claude, which includes a confidence score in each plan
4. **Auto-approve high-confidence plans** (confidence >= threshold) and execute immediately
5. Route lower-confidence plans to `vault/Pending_Approval/` for human review
6. **Send email replies** for approved plans that include a reply draft
7. Archive to `vault/Done/`
8. **Learn from rejections** — analyze rejected plans and store learnings in Agent Memory

Open the `vault/` folder in Obsidian to see your dashboard.

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

## Vault Structure

```
vault/
├── Needs_Action/       # New items detected by watchers
├── Plans/              # Claude-generated plans
├── Pending_Approval/   # Awaiting human review
├── Approved/           # Human-approved actions
├── Rejected/           # Human-rejected plans for review
├── Done/               # Completed items
├── Logs/               # Daily JSON activity logs
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

**Platinum Tier** — Gmail watcher with reply sending, file watcher, self-review loops, confidence-based auto-approve for high-confidence plans, Obsidian vault with approval pipeline.

## License

MIT
