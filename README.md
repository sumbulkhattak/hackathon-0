# Digital FTE — Bronze Tier

> Your life and business on autopilot. Local-first, agent-driven, human-in-the-loop.

An autonomous AI agent that monitors your Gmail, creates actionable plans using Claude, and routes decisions through a human-approval pipeline — all powered by an Obsidian vault.

## Architecture

```
Gmail ──► Gmail Watcher ──► vault/Needs_Action/
                                    │
                            Orchestrator + Claude
                                    │
                            vault/Pending_Approval/
                                    │
                              Human reviews
                                    │
                            vault/Approved/ ──► vault/Done/
```

**Four layers:**
1. **Perception** — Gmail Watcher polls for new emails
2. **Reasoning** — Claude Code analyzes emails and generates plans
3. **Action** — Approved plans are executed (Bronze: logged)
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
3. Process them with Claude, creating plans in `vault/Pending_Approval/`
4. Wait for you to review — move approved files to `vault/Approved/`
5. Execute and archive to `vault/Done/`

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

## Vault Structure

```
vault/
├── Needs_Action/       # New items detected by watchers
├── Plans/              # Claude-generated plans
├── Pending_Approval/   # Awaiting human review
├── Approved/           # Human-approved actions
├── Done/               # Completed items
├── Logs/               # Daily JSON activity logs
└── Company_Handbook.md # Rules for Claude's behavior
```

## Security

- Credentials stored in `credentials/` (gitignored)
- All secrets in `.env` (gitignored)
- Human-in-the-loop: all email actions require approval
- Activity logged to `vault/Logs/`

## Tier Declaration

**Bronze Tier** — Single Gmail watcher, basic Claude integration, Obsidian vault with approval pipeline.

## License

MIT
