"""Tests for Odoo Community MCP Server."""
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture
def vault(tmp_path):
    """Create a vault with Logs directory."""
    (tmp_path / "Logs").mkdir()
    return tmp_path


def test_odoo_client_validate_credentials_missing():
    """OdooClient should report invalid when credentials are missing."""
    sys.path.insert(0, str(Path(__file__).parent.parent / "mcp_servers"))
    from mcp_servers.odoo_server import OdooClient
    client = OdooClient(url="", db="", username="", password="")
    assert client.validate_credentials() is False


def test_odoo_client_validate_credentials_present():
    """OdooClient should report valid when all credentials are set."""
    from mcp_servers.odoo_server import OdooClient
    client = OdooClient(
        url="http://localhost:8069",
        db="testdb",
        username="admin",
        password="admin",
    )
    assert client.validate_credentials() is True


def test_create_invoice_no_credentials():
    """create_invoice should fail gracefully without credentials."""
    from mcp_servers.odoo_server import OdooClient
    client = OdooClient(url="", db="", username="", password="")
    result = client.create_invoice("Test Partner", "Widget", 1, 100.0)
    assert result["success"] is False
    assert "not configured" in result["error"]


def test_list_invoices_no_credentials():
    """list_invoices should fail gracefully without credentials."""
    from mcp_servers.odoo_server import OdooClient
    client = OdooClient(url="", db="", username="", password="")
    result = client.list_invoices()
    assert result["success"] is False


def test_get_invoice_no_credentials():
    """get_invoice should fail gracefully without credentials."""
    from mcp_servers.odoo_server import OdooClient
    client = OdooClient(url="", db="", username="", password="")
    result = client.get_invoice(1)
    assert result["success"] is False


def test_get_balance_no_credentials():
    """get_balance should fail gracefully without credentials."""
    from mcp_servers.odoo_server import OdooClient
    client = OdooClient(url="", db="", username="", password="")
    result = client.get_balance_summary()
    assert result["success"] is False


def test_search_partners_no_credentials():
    """search_partners should fail gracefully without credentials."""
    from mcp_servers.odoo_server import OdooClient
    client = OdooClient(url="", db="", username="", password="")
    result = client.search_partners("test")
    assert result["success"] is False


def test_mcp_create_invoice_tool(vault, monkeypatch):
    """MCP create_invoice tool should return JSON."""
    monkeypatch.setenv("VAULT_PATH", str(vault))
    monkeypatch.setenv("ODOO_URL", "")
    from mcp_servers.odoo_server import create_invoice
    result = json.loads(create_invoice("Partner", "Widget", 1, 50.0))
    assert result["success"] is False  # No credentials


def test_mcp_list_invoices_tool(monkeypatch):
    """MCP list_invoices tool should return JSON."""
    monkeypatch.setenv("ODOO_URL", "")
    from mcp_servers.odoo_server import list_invoices
    result = json.loads(list_invoices())
    assert result["success"] is False


def test_mcp_get_balance_tool(monkeypatch):
    """MCP get_balance tool should return JSON."""
    monkeypatch.setenv("ODOO_URL", "")
    from mcp_servers.odoo_server import get_balance
    result = json.loads(get_balance())
    assert result["success"] is False


def test_mcp_search_partners_tool(monkeypatch):
    """MCP search_partners tool should return JSON."""
    monkeypatch.setenv("ODOO_URL", "")
    from mcp_servers.odoo_server import search_partners
    result = json.loads(search_partners("test"))
    assert result["success"] is False
