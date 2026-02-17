"""Odoo Community MCP Server — exposes accounting operations as tools for Claude Code.

Connects to Odoo Community via JSON-RPC (XML-RPC fallback) for:
- create_invoice: Create a customer invoice
- list_invoices: List recent invoices
- get_balance: Get account balance summary
- search_partners: Search contacts/partners
- get_invoice: Get invoice details by ID

Usage:
    python mcp_servers/odoo_server.py

Requires env vars: ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD
"""
import json
import logging
import os
import sys
import xmlrpc.client
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import log_action

logger = logging.getLogger("mcp.odoo_server")

mcp = FastMCP("Digital FTE Odoo Accounting Server")

# Vault path from environment
VAULT_PATH = Path(os.getenv("VAULT_PATH", "./vault")).resolve()


class OdooClient:
    """Client for Odoo Community XML-RPC API."""

    def __init__(
        self,
        url: str | None = None,
        db: str | None = None,
        username: str | None = None,
        password: str | None = None,
    ):
        self.url = url or os.getenv("ODOO_URL", "")
        self.db = db or os.getenv("ODOO_DB", "")
        self.username = username or os.getenv("ODOO_USERNAME", "")
        self.password = password or os.getenv("ODOO_PASSWORD", "")
        self._uid = None

    def validate_credentials(self) -> bool:
        """Check if all Odoo credentials are configured."""
        return all([self.url, self.db, self.username, self.password])

    def authenticate(self) -> int:
        """Authenticate with Odoo and return user ID."""
        if not self.validate_credentials():
            raise ConnectionError("Odoo credentials not configured")
        common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        uid = common.authenticate(self.db, self.username, self.password, {})
        if not uid:
            raise ConnectionError("Odoo authentication failed")
        self._uid = uid
        return uid

    def execute(self, model: str, method: str, *args, **kwargs):
        """Execute an Odoo RPC call."""
        if self._uid is None:
            self.authenticate()
        models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")
        return models.execute_kw(
            self.db, self._uid, self.password, model, method, list(args), kwargs
        )

    def create_invoice(
        self,
        partner_name: str,
        product_name: str,
        quantity: float = 1.0,
        unit_price: float = 0.0,
    ) -> dict:
        """Create a customer invoice in Odoo.

        Returns dict with invoice_id and status.
        """
        if not self.validate_credentials():
            return {"success": False, "error": "Odoo credentials not configured"}

        try:
            self.authenticate()

            # Find or create partner
            partners = self.execute(
                "res.partner", "search_read",
                [["name", "=", partner_name]],
                fields=["id", "name"],
                limit=1,
            )
            if partners:
                partner_id = partners[0]["id"]
            else:
                partner_id = self.execute(
                    "res.partner", "create",
                    [{"name": partner_name}],
                )

            # Create invoice
            invoice_id = self.execute(
                "account.move", "create",
                [{
                    "move_type": "out_invoice",
                    "partner_id": partner_id,
                    "invoice_line_ids": [(0, 0, {
                        "name": product_name,
                        "quantity": quantity,
                        "price_unit": unit_price,
                    })],
                }],
            )

            return {
                "success": True,
                "invoice_id": invoice_id,
                "partner": partner_name,
                "total": quantity * unit_price,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_invoices(self, limit: int = 10) -> dict:
        """List recent customer invoices."""
        if not self.validate_credentials():
            return {"success": False, "error": "Odoo credentials not configured"}

        try:
            self.authenticate()
            invoices = self.execute(
                "account.move", "search_read",
                [["move_type", "=", "out_invoice"]],
                fields=["id", "name", "partner_id", "amount_total", "state", "invoice_date"],
                limit=limit,
                order="create_date desc",
            )
            return {
                "success": True,
                "count": len(invoices),
                "invoices": invoices,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_invoice(self, invoice_id: int) -> dict:
        """Get details of a specific invoice."""
        if not self.validate_credentials():
            return {"success": False, "error": "Odoo credentials not configured"}

        try:
            self.authenticate()
            invoices = self.execute(
                "account.move", "read",
                [invoice_id],
                fields=["id", "name", "partner_id", "amount_total", "state",
                         "invoice_date", "invoice_line_ids"],
            )
            if not invoices:
                return {"success": False, "error": f"Invoice {invoice_id} not found"}
            return {"success": True, "invoice": invoices[0]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_balance_summary(self) -> dict:
        """Get account balance summary."""
        if not self.validate_credentials():
            return {"success": False, "error": "Odoo credentials not configured"}

        try:
            self.authenticate()
            # Get receivable and payable totals
            invoices = self.execute(
                "account.move", "search_read",
                [["move_type", "=", "out_invoice"], ["state", "=", "posted"]],
                fields=["amount_total", "amount_residual"],
            )
            total_invoiced = sum(inv["amount_total"] for inv in invoices)
            total_outstanding = sum(inv["amount_residual"] for inv in invoices)

            bills = self.execute(
                "account.move", "search_read",
                [["move_type", "=", "in_invoice"], ["state", "=", "posted"]],
                fields=["amount_total", "amount_residual"],
            )
            total_bills = sum(bill["amount_total"] for bill in bills)
            total_payable = sum(bill["amount_residual"] for bill in bills)

            return {
                "success": True,
                "receivable": {
                    "total_invoiced": total_invoiced,
                    "outstanding": total_outstanding,
                },
                "payable": {
                    "total_bills": total_bills,
                    "outstanding": total_payable,
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def search_partners(self, query: str, limit: int = 10) -> dict:
        """Search contacts/partners by name."""
        if not self.validate_credentials():
            return {"success": False, "error": "Odoo credentials not configured"}

        try:
            self.authenticate()
            partners = self.execute(
                "res.partner", "search_read",
                [["name", "ilike", query]],
                fields=["id", "name", "email", "phone"],
                limit=limit,
            )
            return {"success": True, "count": len(partners), "partners": partners}
        except Exception as e:
            return {"success": False, "error": str(e)}


# MCP Tool definitions

@mcp.tool()
def create_invoice(partner_name: str, product_name: str, quantity: float = 1.0, unit_price: float = 0.0) -> str:
    """Create a customer invoice in Odoo.

    Args:
        partner_name: Customer/partner name.
        product_name: Description of the product or service.
        quantity: Number of units (default 1).
        unit_price: Price per unit.
    """
    client = OdooClient()
    result = client.create_invoice(partner_name, product_name, quantity, unit_price)
    if result.get("success"):
        log_action(
            logs_dir=VAULT_PATH / "Logs",
            actor="mcp_odoo_server",
            action="invoice_created",
            source="mcp_tool",
            result=f"{partner_name}:{result.get('invoice_id')}",
        )
    return json.dumps(result)


@mcp.tool()
def list_invoices(limit: int = 10) -> str:
    """List recent customer invoices from Odoo.

    Args:
        limit: Maximum number of invoices to return (default 10).
    """
    client = OdooClient()
    return json.dumps(client.list_invoices(limit))


@mcp.tool()
def get_invoice(invoice_id: int) -> str:
    """Get details of a specific invoice by ID.

    Args:
        invoice_id: The Odoo invoice ID.
    """
    client = OdooClient()
    return json.dumps(client.get_invoice(invoice_id))


@mcp.tool()
def get_balance() -> str:
    """Get account balance summary showing receivables and payables."""
    client = OdooClient()
    return json.dumps(client.get_balance_summary())


@mcp.tool()
def search_partners(query: str, limit: int = 10) -> str:
    """Search contacts/partners in Odoo by name.

    Args:
        query: Name to search for (partial match).
        limit: Maximum results (default 10).
    """
    client = OdooClient()
    return json.dumps(client.search_partners(query, limit))


if __name__ == "__main__":
    mcp.run()
