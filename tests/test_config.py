import os
import pytest


def test_config_loads_vault_path(tmp_path, monkeypatch):
    """Config should read VAULT_PATH from environment."""
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    from src.config import load_config
    cfg = load_config()
    assert cfg.vault_path == tmp_path


def test_config_defaults(monkeypatch):
    """Config should provide sensible defaults when env vars missing."""
    monkeypatch.delenv("VAULT_PATH", raising=False)
    monkeypatch.delenv("GMAIL_CHECK_INTERVAL", raising=False)
    monkeypatch.delenv("GMAIL_FILTER", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    from src.config import load_config
    cfg = load_config()
    assert cfg.vault_path.name == "vault"
    assert cfg.gmail_check_interval == 60
    assert cfg.gmail_filter == "is:unread"
    assert cfg.log_level == "INFO"


def test_config_gmail_interval_from_env(monkeypatch):
    """Config should parse GMAIL_CHECK_INTERVAL as int."""
    monkeypatch.setenv("GMAIL_CHECK_INTERVAL", "30")
    from src.config import load_config
    cfg = load_config()
    assert cfg.gmail_check_interval == 30


def test_config_loads_daily_send_limit(monkeypatch):
    """Config should read DAILY_SEND_LIMIT from environment."""
    monkeypatch.setenv("DAILY_SEND_LIMIT", "50")
    from src.config import load_config
    cfg = load_config()
    assert cfg.daily_send_limit == 50


def test_config_daily_send_limit_default(monkeypatch):
    """Config should default daily_send_limit to 20."""
    monkeypatch.delenv("DAILY_SEND_LIMIT", raising=False)
    from src.config import load_config
    cfg = load_config()
    assert cfg.daily_send_limit == 20
