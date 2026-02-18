"""Tests for secrets isolation — credential validation per work zone."""
import os
import pytest


def test_cloud_zone_warns_on_execution_credentials(monkeypatch):
    """Cloud zone should warn when execution credentials are present."""
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "tok_12345")
    monkeypatch.setenv("TWITTER_API_KEY", "key_xyz")
    from src.secrets_isolation import validate_credentials
    report = validate_credentials("cloud")
    assert report.valid is True
    assert len(report.warnings) >= 2
    assert any("LINKEDIN_ACCESS_TOKEN" in w for w in report.warnings)
    assert any("TWITTER_API_KEY" in w for w in report.warnings)


def test_cloud_zone_no_warnings_when_clean(monkeypatch):
    """Cloud zone should produce no warnings when execution credentials are absent."""
    for key in ["LINKEDIN_ACCESS_TOKEN", "FACEBOOK_PAGE_TOKEN", "TWITTER_API_KEY",
                "TWITTER_API_SECRET", "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_SECRET",
                "ODOO_URL", "ODOO_DB", "ODOO_USERNAME", "ODOO_PASSWORD",
                "DAILY_SEND_LIMIT"]:
        monkeypatch.delenv(key, raising=False)
    from src.secrets_isolation import validate_credentials
    report = validate_credentials("cloud")
    assert report.valid is True
    assert len(report.warnings) == 0


def test_local_zone_always_valid(monkeypatch):
    """Local zone should always be valid regardless of credentials."""
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "tok_12345")
    from src.secrets_isolation import validate_credentials
    report = validate_credentials("local")
    assert report.valid is True


def test_local_zone_warns_missing_gmail_creds(monkeypatch, tmp_path):
    """Local zone should warn if Gmail credentials file is missing."""
    monkeypatch.chdir(tmp_path)
    from src.secrets_isolation import validate_credentials
    report = validate_credentials("local")
    assert report.valid is True
    assert any("client_secret.json" in w for w in report.warnings)


def test_unknown_zone_blocked():
    """Unknown work zone should be blocked."""
    from src.secrets_isolation import validate_credentials
    report = validate_credentials("unknown")
    assert report.valid is False
    assert len(report.blocked) >= 1
    assert "unknown" in report.blocked[0].lower() or "Unknown" in report.blocked[0]


def test_credential_report_fields():
    """CredentialReport should have all expected fields."""
    from src.secrets_isolation import CredentialReport
    report = CredentialReport(zone="local", valid=True, warnings=[], blocked=[])
    assert report.zone == "local"
    assert report.valid is True
    assert report.warnings == []
    assert report.blocked == []


def test_cloud_zone_capabilities():
    """Cloud zone should block execution capabilities."""
    from src.secrets_isolation import get_zone_capabilities
    caps = get_zone_capabilities("cloud")
    assert caps["read_email"] is True
    assert caps["draft_plans"] is True
    assert caps["send_email"] is False
    assert caps["execute_actions"] is False
    assert caps["social_media_post"] is False
    assert caps["odoo_operations"] is False
    assert caps["approve_reject"] is False


def test_local_zone_capabilities():
    """Local zone should allow all capabilities."""
    from src.secrets_isolation import get_zone_capabilities
    caps = get_zone_capabilities("local")
    assert all(v is True for v in caps.values())


def test_cloud_zone_has_correct_report_zone():
    """Credential report zone field should match input."""
    from src.secrets_isolation import validate_credentials
    report = validate_credentials("cloud")
    assert report.zone == "cloud"
