# Skill: Odoo Community Accounting

## Description
Integrates with Odoo Community ERP via JSON-RPC/XML-RPC for accounting operations: creating invoices, tracking receivables/payables, searching partners, and generating balance summaries.

## Trigger
- User requests invoice creation, payment tracking, or financial reports
- Orchestrator detects financial/accounting context in action items
- CEO Briefing requests financial summary data

## Configuration
```env
ODOO_URL=http://localhost:8069
ODOO_DB=mycompany
ODOO_USERNAME=admin
ODOO_PASSWORD=admin_password
```

## MCP Tools (via mcp_servers/odoo_server.py)
| Tool | Description |
|------|-------------|
| `create_invoice` | Create a customer invoice (partner, product, qty, price) |
| `list_invoices` | List recent invoices with status and amounts |
| `get_invoice` | Get detailed invoice by ID |
| `get_balance` | Account balance summary (receivables + payables) |
| `search_partners` | Search contacts/partners by name |

## Safety Rules
- Invoice creation always requires human approval (routed to Pending_Approval/)
- Cloud zone cannot execute Odoo operations (local zone only)
- Credentials validated at startup via secrets isolation

## Implementation
- Module: `mcp_servers/odoo_server.py`
  - `OdooClient` class with XML-RPC connection
  - 5 MCP tools for Claude Code integration
- Tests: `tests/test_odoo_mcp.py` (12 tests)
