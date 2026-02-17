# Skill: MCP Email Server

## Description
A Model Context Protocol (MCP) server that exposes email and vault operations as tools Claude Code can invoke directly.

## Available Tools

### send_email
Send a threaded Gmail reply with rate limiting.
- **Input:** gmail_id, to, subject, body
- **Output:** success/error JSON

### search_emails
Search Gmail with any query.
- **Input:** query (Gmail search syntax), max_results
- **Output:** list of matching emails with id, from, subject, date, snippet

### list_pending
List all files awaiting human review in Pending_Approval/.
- **Output:** list of pending items with filename, source, confidence, action

### get_vault_status
Get current vault folder counts and system status.
- **Output:** folder counts, active/idle status, items to process

## Setup
Add to your Claude Code MCP configuration:
```json
{
  "mcpServers": {
    "digital-fte-email": {
      "command": "python",
      "args": ["mcp_servers/email_server.py"],
      "env": {
        "VAULT_PATH": "./vault",
        "DAILY_SEND_LIMIT": "20"
      }
    }
  }
}
```

## Running Standalone
```bash
python mcp_servers/email_server.py
```

## Implementation
- Server: `mcp_servers/email_server.py`
- Uses: `src/gmail_sender.py`, `src/dashboard.py`, `src/utils.py`, `src/auth.py`
- Protocol: MCP (Model Context Protocol) via `mcp` Python SDK
