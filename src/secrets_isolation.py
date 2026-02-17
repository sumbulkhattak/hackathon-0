"""Secrets isolation — ensures cloud and local zones have appropriate credentials.

Cloud zone: read-only credentials (Gmail read + Claude for drafting)
Local zone: full credentials (Gmail send, social media, Odoo execution)

Validates at startup that credentials match the configured work zone.
"""
import logging
import os
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("digital_fte.secrets_isolation")

# Credential categories by zone
CLOUD_ALLOWED = {
    "CLAUDE_MODEL",
    "VAULT_PATH",
    "GMAIL_CHECK_INTERVAL",
    "GMAIL_FILTER",
    "LOG_LEVEL",
    "WORK_ZONE",
    "AUTO_APPROVE_THRESHOLD",
    "VIP_SENDERS",
    "WEB_ENABLED",
    "WEB_PORT",
    "FILE_WATCH_ENABLED",
    "FILE_WATCH_DRY_RUN",
}

LOCAL_ONLY = {
    "DAILY_SEND_LIMIT",
    "LINKEDIN_ACCESS_TOKEN",
    "FACEBOOK_PAGE_TOKEN",
    "TWITTER_API_KEY",
    "TWITTER_API_SECRET",
    "TWITTER_ACCESS_TOKEN",
    "TWITTER_ACCESS_SECRET",
    "ODOO_URL",
    "ODOO_DB",
    "ODOO_USERNAME",
    "ODOO_PASSWORD",
}


@dataclass
class CredentialReport:
    """Result of credential validation."""
    zone: str
    valid: bool
    warnings: list[str]
    blocked: list[str]


def validate_credentials(work_zone: str) -> CredentialReport:
    """Validate that current credentials match the work zone.

    Cloud zone:
    - Should NOT have execution credentials (social media, Odoo)
    - Warns if execution credentials are present (information leak risk)

    Local zone:
    - No restrictions — can have all credentials
    - Warns if critical execution credentials are missing

    Returns CredentialReport with validation results.
    """
    warnings = []
    blocked = []

    if work_zone == "cloud":
        # Cloud zone should not have execution credentials
        for key in LOCAL_ONLY:
            value = os.getenv(key, "")
            if value.strip():
                warnings.append(
                    f"Cloud zone has execution credential '{key}' set — "
                    f"consider removing for security isolation"
                )
        logger.info("Cloud zone credential check complete")

    elif work_zone == "local":
        # Local zone: warn about missing credentials that might be needed
        gmail_creds = Path("credentials/client_secret.json")
        if not gmail_creds.exists():
            warnings.append(
                "Gmail credentials not found at credentials/client_secret.json — "
                "email sending will not work"
            )
        logger.info("Local zone credential check complete")

    else:
        blocked.append(f"Unknown work zone: '{work_zone}'. Must be 'cloud' or 'local'.")

    return CredentialReport(
        zone=work_zone,
        valid=len(blocked) == 0,
        warnings=warnings,
        blocked=blocked,
    )


def get_zone_capabilities(work_zone: str) -> dict:
    """Return what operations are allowed in the current zone.

    Returns dict mapping capability names to booleans.
    """
    if work_zone == "cloud":
        return {
            "read_email": True,
            "draft_plans": True,
            "send_email": False,
            "execute_actions": False,
            "social_media_post": False,
            "odoo_operations": False,
            "approve_reject": False,
        }
    else:  # local
        return {
            "read_email": True,
            "draft_plans": True,
            "send_email": True,
            "execute_actions": True,
            "social_media_post": True,
            "odoo_operations": True,
            "approve_reject": True,
        }
