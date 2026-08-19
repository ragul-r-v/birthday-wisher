"""
Gmail API OAuth2 Authentication Helper.

Loads OAuth2 credentials from environment variables (GMAIL_TOKEN_JSON and
GMAIL_CREDENTIALS_JSON) and returns an authenticated Gmail API service object.

The refresh token stored in GMAIL_TOKEN_JSON is long-lived and automatically
renews access tokens, eliminating the recurring 535 Bad Credentials errors
that plague SMTP App Passwords.
"""

import json
import os
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Gmail API scope for sending email
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def get_gmail_service():
    """
    Authenticates with the Gmail API using OAuth2 credentials from environment
    variables and returns an authenticated Gmail API service object.

    Environment Variables:
        GMAIL_TOKEN_JSON: JSON string containing the OAuth2 token (with
                          refresh_token, access_token, client_id, client_secret, etc.)
        GMAIL_CREDENTIALS_JSON: (Optional) JSON string containing the OAuth2 client
                                credentials (client_id, client_secret). Used as a
                                fallback if GMAIL_TOKEN_JSON doesn't include them.

    Returns:
        googleapiclient.discovery.Resource: Authenticated Gmail API service object.

    Raises:
        SystemExit: If credentials are missing, invalid, or cannot be refreshed.
    """
    token_json_str = os.environ.get("GMAIL_TOKEN_JSON", "").strip()

    if not token_json_str:
        return None  # Signal caller to use SMTP fallback

    try:
        token_data = json.loads(token_json_str)
    except json.JSONDecodeError as e:
        print(f"ERROR: GMAIL_TOKEN_JSON is not valid JSON: {e}")
        sys.exit(1)

    # If client_id/client_secret are missing from token, try GMAIL_CREDENTIALS_JSON
    if "client_id" not in token_data or "client_secret" not in token_data:
        creds_json_str = os.environ.get("GMAIL_CREDENTIALS_JSON", "").strip()
        if creds_json_str:
            try:
                creds_data = json.loads(creds_json_str)
                # Handle the nested "installed" or "web" key format from Google
                if "installed" in creds_data:
                    creds_data = creds_data["installed"]
                elif "web" in creds_data:
                    creds_data = creds_data["web"]

                token_data["client_id"] = creds_data.get("client_id", "")
                token_data["client_secret"] = creds_data.get("client_secret", "")
            except json.JSONDecodeError as e:
                print(f"ERROR: GMAIL_CREDENTIALS_JSON is not valid JSON: {e}")
                sys.exit(1)

    # Validate required fields
    required_fields = ["refresh_token", "client_id", "client_secret"]
    missing = [f for f in required_fields if not token_data.get(f)]
    if missing:
        print(f"ERROR: GMAIL_TOKEN_JSON is missing required fields: {', '.join(missing)}")
        print("Please re-run setup_gmail_token.py to generate a complete token.")
        sys.exit(1)

    # Build credentials object
    creds = Credentials(
        token=token_data.get("token", ""),
        refresh_token=token_data["refresh_token"],
        token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=token_data["client_id"],
        client_secret=token_data["client_secret"],
        scopes=SCOPES,
    )

    # Refresh the access token if expired (or if no access token exists yet)
    if not creds.valid:
        if creds.expired or not creds.token:
            try:
                creds.refresh(Request())
                print("Gmail API: Access token refreshed successfully.")
            except Exception as e:
                print(f"ERROR: Failed to refresh Gmail API access token: {e}")
                print("You may need to re-run setup_gmail_token.py to generate a new token.")
                sys.exit(1)
        else:
            print("ERROR: Gmail API credentials are invalid and cannot be refreshed.")
            sys.exit(1)

    try:
        service = build("gmail", "v1", credentials=creds)
        print("Gmail API: Service authenticated successfully!")
        return service
    except Exception as e:
        print(f"ERROR: Failed to build Gmail API service: {e}")
        sys.exit(1)
