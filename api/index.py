"""Vercel serverless entry point — wraps FastAPI app for deployment."""
from pathlib import Path
import sys
import os

# Ensure project root is on path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.web import app, create_app
from setup_vault import setup_vault

# Initialize vault
vault_path = Path(os.getenv("VAULT_PATH", str(project_root / "vault"))).resolve()
setup_vault(vault_path)
create_app(vault_path)
