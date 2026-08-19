"""
One-time setup script to generate Gmail API OAuth2 token.

Run this locally (NOT in CI) to complete the OAuth2 consent flow
and generate a token.json file. The contents of this file should
then be stored as the GMAIL_TOKEN_JSON GitHub repository secret.

Prerequisites:
    1. You have a Google Cloud project with the Gmail API enabled.
    2. You downloaded the OAuth2 client credentials JSON file
       (Desktop application type) and saved it as 'credentials.json'
       in this directory.

Usage:
    python setup_gmail_token.py

After running, the script will:
    1. Open your browser for Google OAuth consent
    2. Save the refresh token to 'token.json'
    3. Print the JSON to copy into GitHub Secrets
"""

import json
import os
import sys

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("ERROR: Required packages not installed.")
    print("Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    sys.exit(1)

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"


def main():
    print("=" * 60)
    print("  Gmail API OAuth2 Token Setup")
    print("=" * 60)

    # Check for existing token
    creds = None
    if os.path.exists(TOKEN_FILE):
        print(f"\nFound existing {TOKEN_FILE}, attempting to load...")
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # If valid, no need to re-authenticate
    if creds and creds.valid:
        print("Existing token is still valid!")
    elif creds and creds.expired and creds.refresh_token:
        print("Token expired, refreshing...")
        try:
            creds.refresh(Request())
            print("Token refreshed successfully!")
        except Exception as e:
            print(f"Refresh failed ({e}), need to re-authenticate.")
            creds = None
    else:
        creds = None

    # Need new authentication
    if creds is None:
        if not os.path.exists(CREDENTIALS_FILE):
            print(f"\nERROR: '{CREDENTIALS_FILE}' not found!")
            print("\nTo get this file:")
            print("  1. Go to https://console.cloud.google.com/apis/credentials")
            print("  2. Create OAuth 2.0 Client ID (Desktop application)")
            print("  3. Download the JSON file")
            print(f"  4. Save it as '{CREDENTIALS_FILE}' in this directory")
            print(f"\nSee SETUP_GMAIL_API.md for detailed instructions.")
            sys.exit(1)

        print(f"\nStarting OAuth2 flow using {CREDENTIALS_FILE}...")
        print("A browser window will open for Google account authorization.\n")

        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        print("\nAuthorization successful!")

    # Save token
    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
    }

    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)
    print(f"\nToken saved to {TOKEN_FILE}")

    # Display for GitHub Secrets
    compact_json = json.dumps(token_data)
    print("\n" + "=" * 60)
    print("  COPY THE FOLLOWING INTO GITHUB SECRETS")
    print("=" * 60)
    print(f"\nSecret Name: GMAIL_TOKEN_JSON")
    print(f"Secret Value (copy everything between the dashes):")
    print("-" * 60)
    print(compact_json)
    print("-" * 60)

    # Also print credentials.json content for GMAIL_CREDENTIALS_JSON
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, "r") as f:
            creds_content = f.read().strip()
        print(f"\nSecret Name: GMAIL_CREDENTIALS_JSON")
        print(f"Secret Value (copy everything between the dashes):")
        print("-" * 60)
        print(creds_content)
        print("-" * 60)

    print(f"\n⚠️  IMPORTANT: Add both secrets to your GitHub repository:")
    print(f"   Repository → Settings → Secrets and variables → Actions")
    print(f"\n⚠️  SECURITY: Do NOT commit {TOKEN_FILE} or {CREDENTIALS_FILE} to git!")
    print(f"   They are already in .gitignore.\n")


if __name__ == "__main__":
    main()
