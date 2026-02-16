"""Gmail OAuth 2.0 authentication helper."""
import logging
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger("digital_fte.auth")
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def get_gmail_service(credentials_dir: Path):
    credentials_dir.mkdir(parents=True, exist_ok=True)
    token_path = credentials_dir / "token.json"
    client_secret_path = credentials_dir / "client_secret.json"
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired Gmail token...")
            creds.refresh(Request())
        else:
            if not client_secret_path.exists():
                raise FileNotFoundError(
                    f"Missing {client_secret_path}. Download your OAuth client "
                    f"secret from Google Cloud Console and save it there.\n"
                    f"Guide: https://developers.google.com/gmail/api/quickstart/python"
                )
            logger.info("Starting OAuth flow — a browser window will open...")
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_path), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json())
        logger.info(f"Token saved to {token_path}")
    return build("gmail", "v1", credentials=creds)
