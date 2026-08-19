import os
import re
import time
from datetime import datetime
import pandas
import random
import smtplib
import sys
import base64
from email.message import EmailMessage
from email.mime.text import MIMEText

# Set stdout/stderr encoding to UTF-8 for safe emoji logging across all operating systems
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')


def emit_github_annotation(title, message, level="error"):
    """Emits GitHub Actions workflow annotations if running in GitHub Actions CI environment."""
    if os.environ.get("GITHUB_ACTIONS") == "true":
        # Escape newlines for GitHub Actions annotation format
        clean_msg = message.replace("\n", "%0A")
        print(f"::{level} title={title}::{clean_msg}")


def write_github_summary(markdown_content):
    """Appends Markdown content to the GitHub Actions Job Summary if available."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path and os.path.exists(os.path.dirname(summary_path or "")):
        try:
            with open(summary_path, "a", encoding="utf-8") as f:
                f.write(markdown_content + "\n")
        except Exception:
            pass


def sanitize_email(email_str):
    if not email_str:
        return ""
    # Strip quotes, invisible zero-width chars, and leading/trailing whitespace
    cleaned = re.sub(r'[\u200b\ufeff\u200e\u200f\xa0]', '', email_str)
    return cleaned.strip().strip("'\"")


def sanitize_password(pwd_str):
    if not pwd_str:
        return ""
    # Remove invisible zero-width chars and non-breaking spaces
    cleaned = re.sub(r'[\u200b\ufeff\u200e\u200f\xa0]', '', pwd_str)
    # App passwords can contain spaces (e.g. "abcd efgh ijkl mnop"); remove all whitespace and outer quotes
    return re.sub(r'\s+', '', cleaned.strip().strip("'\""))


def get_today_date():
    # Ensure timezone is IST (Asia/Kolkata) matching the workflow schedule (~6:00 AM IST)
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Kolkata"))
    except Exception:
        return datetime.now()


def send_email_gmail_api(service, sender_email, to_email, subject, body):
    """Send an email using the Gmail API.

    Args:
        service: Authenticated Gmail API service object.
        sender_email: Sender's email address (used for the 'From' header).
        to_email: Recipient email address.
        subject: Email subject line.
        body: Email body text.
    """
    msg = MIMEText(body)
    msg["To"] = to_email
    msg["From"] = sender_email
    msg["Subject"] = subject

    # Gmail API requires base64url-encoded email
    raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    service.users().messages().send(
        userId="me",
        body={"raw": raw_message}
    ).execute()


def get_sender_email_from_gmail_api(service):
    """Retrieve the authenticated user's email address from the Gmail API profile."""
    try:
        profile = service.users().getProfile(userId="me").execute()
        return profile.get("emailAddress", "")
    except Exception:
        return ""


def connect_smtp(email, password):
    """Connect and authenticate to Gmail SMTP server with retry logic.

    Returns:
        tuple: (connection, auth_failed) — connection is the SMTP object or None,
               auth_failed is True if authentication was explicitly rejected.
    """
    connection = None
    max_retries = 3
    auth_failed = False

    for attempt in range(1, max_retries + 1):
        try:
            print(f"Connecting to Gmail SMTP server (Attempt {attempt}/{max_retries})...")
            connection = smtplib.SMTP("smtp.gmail.com", 587, timeout=30)
            connection.starttls()
            connection.login(email, password)
            print("SMTP Authentication successful!")
            return connection, False
        except smtplib.SMTPAuthenticationError as auth_err:
            err_title = "SMTP Authentication Failed (535 Bad Credentials)"
            err_details = (
                f"Gmail rejected the username or password ({auth_err}).\n\n"
                "Troubleshooting Steps:\n"
                "1. Go to your Google Account (Security -> 2-Step Verification -> App Passwords).\n"
                "2. Generate a new 16-character App Password for 'Mail'.\n"
                "3. Go to GitHub Repository -> Settings -> Secrets and variables -> Actions.\n"
                "4. Update the 'PASSWORD' secret with your new 16-character App Password."
            )
            print(f"\nERROR: {err_title}: {auth_err}")
            print("\n" + err_details)

            emit_github_annotation(err_title, f"Gmail rejected login for {email}. Please update your PASSWORD secret in GitHub Repository Secrets.")

            summary_md = (
                f"## ❌ {err_title}\n\n"
                f"**Error Details**: `{auth_err}`\n\n"
                "### 🛠️ How to Fix:\n"
                "1. Visit [Google App Passwords](https://myaccount.google.com/apppasswords).\n"
                "2. Ensure **2-Step Verification** is enabled.\n"
                "3. Generate a new App Password for **Mail**.\n"
                "4. Navigate to your GitHub Repo **Settings** > **Secrets and variables** > **Actions**.\n"
                "5. Set `PASSWORD` secret to your new **16-character App Password** (without quotes or spaces).\n"
            )
            write_github_summary(summary_md)
            return None, True
        except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, TimeoutError, OSError) as net_err:
            print(f"SMTP Connection attempt {attempt} failed: {net_err}")
            if attempt < max_retries:
                time.sleep(2)
            else:
                print("ERROR: Exceeded maximum SMTP connection retries.")
                emit_github_annotation("SMTP Connection Timeout", f"Failed to connect to smtp.gmail.com: {net_err}")
                sys.exit(1)
        except Exception as e:
            print(f"ERROR connecting to SMTP: {e}")
            emit_github_annotation("SMTP Connection Error", str(e))
            sys.exit(1)

    return None, False


def run():
    today = get_today_date()
    RAW_EMAIL = os.environ.get("EMAIL")
    RAW_PASSWORD = os.environ.get("PASSWORD")
    NOTIFY_EMAIL = sanitize_email(os.environ.get("NOTIFY_EMAIL", "t.v.malathi2001@gmail.com"))

    # Determine authentication method: Gmail API (preferred) or SMTP (fallback)
    gmail_service = None
    use_gmail_api = False

    # Try Gmail API first
    gmail_token = os.environ.get("GMAIL_TOKEN_JSON", "").strip()
    if gmail_token:
        print("Gmail API credentials detected. Using OAuth2 authentication...")
        try:
            from gmail_auth import get_gmail_service
            gmail_service = get_gmail_service()
            if gmail_service:
                use_gmail_api = True
                # Get sender email from Gmail API profile
                MY_EMAIL = get_sender_email_from_gmail_api(gmail_service)
                if not MY_EMAIL and RAW_EMAIL:
                    MY_EMAIL = sanitize_email(RAW_EMAIL)
                elif not MY_EMAIL:
                    MY_EMAIL = "me"
                print(f"Authenticated as: {MY_EMAIL}")
        except Exception as e:
            print(f"WARNING: Gmail API setup failed ({e}), falling back to SMTP...")
            gmail_service = None
            use_gmail_api = False

    # Fallback to SMTP if Gmail API is not configured or failed
    if not use_gmail_api:
        if not RAW_EMAIL or not RAW_PASSWORD:
            err_title = "Missing Credentials"
            err_msg = (
                "No authentication method available.\n"
                "Either set GMAIL_TOKEN_JSON (recommended) or EMAIL + PASSWORD secrets.\n"
                "See SETUP_GMAIL_API.md for the recommended Gmail API setup."
            )
            print(f"ERROR: {err_msg}")
            emit_github_annotation(err_title, err_msg)
            write_github_summary(f"### ❌ {err_title}\n{err_msg}")
            sys.exit(1)

        MY_EMAIL = sanitize_email(RAW_EMAIL)
        MY_PASSWORD = sanitize_password(RAW_PASSWORD)

        if not MY_EMAIL or not MY_PASSWORD:
            err_title = "Invalid/Empty Credentials Secret"
            err_msg = "EMAIL or PASSWORD secret resolved to an empty string after sanitization."
            print(f"ERROR: {err_msg}")
            emit_github_annotation(err_title, err_msg)
            sys.exit(1)

        # Pre-flight warning for Google App Password length check
        if len(MY_PASSWORD) != 16:
            warn_title = "Non-Standard App Password Format"
            warn_msg = f"Detected password length of {len(MY_PASSWORD)} chars. Standard Google App Passwords are 16 characters. If authentication fails, generate a new App Password."
            print(f"WARNING: {warn_msg}")
            emit_github_annotation(warn_title, warn_msg, level="warning")

    print(f"Running Birthday Wisher for date: {today.strftime('%Y-%m-%d')} (Month: {today.month}, Day: {today.day})")
    print(f"Authentication method: {'Gmail API (OAuth2)' if use_gmail_api else 'SMTP (App Password)'}")

    if not os.path.exists("birthdays.csv"):
        err_msg = "birthdays.csv file not found!"
        print(f"ERROR: {err_msg}")
        emit_github_annotation("Missing birthdays.csv", err_msg)
        sys.exit(1)

    data = pandas.read_csv("birthdays.csv")

    # Find all matching birthdays for today
    birthday_people = data[
        (data["month"] == today.month) &
        (data["day"] == today.day)
    ]

    print(f"Found {len(birthday_people)} matching birthday(s) for today!")

    if birthday_people.empty:
        print("No birthdays found for today. Exiting cleanly.")
        sys.exit(0)

    # Connect via SMTP if not using Gmail API
    connection = None
    if not use_gmail_api:
        connection, auth_failed = connect_smtp(MY_EMAIL, MY_PASSWORD)
        if auth_failed or connection is None:
            sys.exit(1)

    successful_wishes = []
    failed_wishes = []

    try:
        for index, birthday_person in birthday_people.iterrows():
            name = str(birthday_person["name"]).strip()
            recipient_email = str(birthday_person["email"]).strip()

            file_path = f"letter_templates/letter_{random.randint(1, 3)}.txt"

            with open(file_path, "r", encoding="utf-8") as letter_file:
                contents = letter_file.read()
                contents = contents.replace("[NAME]", name)

            try:
                if use_gmail_api:
                    send_email_gmail_api(
                        gmail_service, MY_EMAIL, recipient_email,
                        "Happy Birthday! 🎉", contents
                    )
                else:
                    msg = EmailMessage()
                    msg["From"] = MY_EMAIL
                    msg["To"] = recipient_email
                    msg["Subject"] = "Happy Birthday! 🎉"
                    msg.set_content(contents)
                    connection.send_message(msg)

                print(f"Email sent successfully to {name} <{recipient_email}>")
                successful_wishes.append(f"{name} ({recipient_email})")
            except Exception as send_err:
                print(f"ERROR sending email to {name} <{recipient_email}>: {send_err}")
                failed_wishes.append(f"{name} ({recipient_email}) - Error: {send_err}")

        # Forward/Notify email feature: Notify NOTIFY_EMAIL about today's birthdays
        if NOTIFY_EMAIL:
            print(f"Sending today's birthday notification summary email to {NOTIFY_EMAIL}...")

            person_list = "\n".join([f"• {name} ({str(row['email']).strip()})" for _, row in birthday_people.iterrows()])

            body_lines = [
                f"Hello,\n",
                f"Here are the birthday celebrants for today ({today.strftime('%Y-%m-%d')}):\n",
                person_list,
                f"\n--- Summary ---",
                f"Total birthdays found: {len(birthday_people)}",
                f"Wishes sent successfully: {len(successful_wishes)}"
            ]

            if failed_wishes:
                body_lines.append(f"Wishes failed: {len(failed_wishes)}")
                body_lines.append("\nFailed details:\n" + "\n".join(failed_wishes))

            body_lines.append("\nBest regards,\nAutomated Birthday Wisher Bot")
            notify_body = "\n".join(body_lines)

            try:
                if use_gmail_api:
                    send_email_gmail_api(
                        gmail_service, MY_EMAIL, NOTIFY_EMAIL,
                        f"🎂 Today's Birthday Alert: {today.strftime('%d %B %Y')}", notify_body
                    )
                else:
                    notify_msg = EmailMessage()
                    notify_msg["From"] = MY_EMAIL
                    notify_msg["To"] = NOTIFY_EMAIL
                    notify_msg["Subject"] = f"🎂 Today's Birthday Alert: {today.strftime('%d %B %Y')}"
                    notify_msg.set_content(notify_body)
                    connection.send_message(notify_msg)

                print(f"Notification summary email sent successfully to {NOTIFY_EMAIL}!")
            except Exception as notify_err:
                print(f"ERROR sending notification email to {NOTIFY_EMAIL}: {notify_err}")

    finally:
        try:
            if connection:
                connection.quit()
        except Exception:
            pass

    # Write success summary to GitHub Actions
    if successful_wishes:
        auth_method = "Gmail API (OAuth2)" if use_gmail_api else "SMTP (App Password)"
        summary_md = (
            f"## ✅ Birthday Wishes Sent Successfully!\n\n"
            f"**Date**: {today.strftime('%d %B %Y')}\n"
            f"**Method**: {auth_method}\n"
            f"**Sent**: {len(successful_wishes)} | **Failed**: {len(failed_wishes)}\n\n"
        )
        if failed_wishes:
            summary_md += "### ⚠️ Failed:\n" + "\n".join(f"- {f}" for f in failed_wishes) + "\n"
        write_github_summary(summary_md)


if __name__ == "__main__":
    run()