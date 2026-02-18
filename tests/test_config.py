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


def test_config_loads_auto_approve_threshold(monkeypatch):
    """Config should read AUTO_APPROVE_THRESHOLD from environment."""
    monkeypatch.setenv("AUTO_APPROVE_THRESHOLD", "0.85")
    from src.config import load_config
    cfg = load_config()
    assert cfg.auto_approve_threshold == 0.85


def test_config_auto_approve_threshold_default(monkeypatch):
    """Config should default auto_approve_threshold to 1.0 (disabled)."""
    monkeypatch.delenv("AUTO_APPROVE_THRESHOLD", raising=False)
    from src.config import load_config
    cfg = load_config()
    assert cfg.auto_approve_threshold == 1.0


def test_config_loads_vip_senders(monkeypatch):
    """Config should parse VIP_SENDERS as a list of emails."""
    monkeypatch.setenv("VIP_SENDERS", "ceo@co.com,client@big.com")
    from src.config import load_config
    cfg = load_config()
    assert cfg.vip_senders == ["ceo@co.com", "client@big.com"]


def test_config_vip_senders_default_empty(monkeypatch):
    """Config should default vip_senders to empty list."""
    monkeypatch.delenv("VIP_SENDERS", raising=False)
    from src.config import load_config
    cfg = load_config()
    assert cfg.vip_senders == []


def test_config_vip_senders_strips_whitespace(monkeypatch):
    """Config should strip whitespace from VIP sender entries."""
    monkeypatch.setenv("VIP_SENDERS", " ceo@co.com , client@big.com ")
    from src.config import load_config
    cfg = load_config()
    assert cfg.vip_senders == ["ceo@co.com", "client@big.com"]


def test_config_web_enabled_default(monkeypatch):
    """Config should default web_enabled to True."""
    monkeypatch.delenv("WEB_ENABLED", raising=False)
    from src.config import load_config
    cfg = load_config()
    assert cfg.web_enabled is True


def test_config_web_port_from_env(monkeypatch):
    """Config should read WEB_PORT from environment."""
    monkeypatch.setenv("WEB_PORT", "3000")
    from src.config import load_config
    cfg = load_config()
    assert cfg.web_port == 3000


def test_config_web_port_default(monkeypatch):
    """Config should default web_port to 8000."""
    monkeypatch.delenv("WEB_PORT", raising=False)
    from src.config import load_config
    cfg = load_config()
    assert cfg.web_port == 8000


def test_config_work_zone_from_env(monkeypatch):
    """Config should read WORK_ZONE from environment."""
    monkeypatch.setenv("WORK_ZONE", "cloud")
    from src.config import load_config
    cfg = load_config()
    assert cfg.work_zone == "cloud"


def test_config_work_zone_default_local(monkeypatch):
    """Config should default work_zone to 'local'."""
    monkeypatch.delenv("WORK_ZONE", raising=False)
    from src.config import load_config
    cfg = load_config()
    assert cfg.work_zone == "local"
