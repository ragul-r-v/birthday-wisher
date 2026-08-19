# Gmail API Setup Guide (OAuth2)

This guide walks you through setting up Gmail API with OAuth2 for the Birthday Wisher. This replaces the old App Password method and **permanently eliminates** the recurring `535 Bad Credentials` errors.

## Why Switch?

| Feature | App Password (Old) | Gmail API OAuth2 (New) |
|---|---|---|
| Token expiry | Expires on password change / 2FA toggle | Refresh token is permanent |
| 535 errors | Frequent | Never |
| Security | Stores actual password | Scoped OAuth token only |
| Setup time | 2 min | 10 min (one-time) |

---

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **Select a project** → **New Project**
3. Name it `Birthday Wisher` (or anything you like)
4. Click **Create**

## Step 2: Enable the Gmail API

1. In your new project, go to **APIs & Services** → **Library**
2. Search for **Gmail API**
3. Click **Gmail API** → **Enable**

## Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Select **External** → **Create**
3. Fill in required fields:
   - **App name**: `Birthday Wisher`
   - **User support email**: Your Gmail address
   - **Developer contact**: Your Gmail address
4. Click **Save and Continue** through remaining steps
5. Under **Test users**, click **Add users** and add **your Gmail address**
6. Click **Save and Continue** → **Back to Dashboard**

## Step 4: Create OAuth2 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. Application type: **Desktop app**
4. Name: `Birthday Wisher Desktop`
5. Click **Create**
6. Click **Download JSON** (⬇️ icon)
7. Save the downloaded file as `credentials.json` in the project root directory

## Step 5: Generate Your Token (One-Time)

Run the setup script locally on your computer:

```bash
# Install dependencies first
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib

# Run the token generator
python setup_gmail_token.py
```

This will:
1. Open your browser for Google login and consent
2. Ask you to authorize the Birthday Wisher to send emails
3. Save the token to `token.json`
4. Display the JSON values to copy into GitHub Secrets

> ⚠️ **Note**: Since the app is in "Testing" mode, Google will show a warning screen. Click **Advanced** → **Go to Birthday Wisher (unsafe)** → **Continue**. This is safe — it's your own app.

## Step 6: Add Secrets to GitHub

Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these two secrets:

### Secret 1: `GMAIL_TOKEN_JSON`
Copy the JSON value printed by `setup_gmail_token.py` (the compact JSON between the dashes).

### Secret 2: `GMAIL_CREDENTIALS_JSON`
Copy the entire contents of your `credentials.json` file.

## Step 7: Verify

1. Go to your repository → **Actions** → **Birthday Wisher**
2. Click **Run workflow** → **Run workflow**
3. Check the logs — you should see:
   ```
   Gmail API credentials detected. Using OAuth2 authentication...
   Gmail API: Access token refreshed successfully.
   Gmail API: Service authenticated successfully!
   Authentication method: Gmail API (OAuth2)
   ```

## Cleanup (Optional)

Once Gmail API is working, you can optionally delete the old `EMAIL` and `PASSWORD` secrets from GitHub. They're kept as a fallback — if `GMAIL_TOKEN_JSON` is missing, the system automatically falls back to SMTP with App Password.

---

## Troubleshooting

### "Token has been expired or revoked"
Re-run `python setup_gmail_token.py` to generate a new token and update the `GMAIL_TOKEN_JSON` secret.

### "Access blocked: Birthday Wisher has not completed the Google verification process"
This happens when too many users try to use the app. Since this is a personal app:
1. Go to [Google Cloud Console](https://console.cloud.google.com/) → **OAuth consent screen**
2. Ensure your Gmail is listed under **Test users**

### "credentials.json not found"
Download the OAuth credentials from Google Cloud Console → **APIs & Services** → **Credentials** → click the download icon next to your OAuth client.

### Still getting 535 errors?
The workflow is falling back to SMTP because `GMAIL_TOKEN_JSON` is not set. Make sure you completed Steps 5-6.
