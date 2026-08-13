import os
import re
import time
from datetime import datetime
import pandas
import random
import smtplib
import sys
from email.message import EmailMessage

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


def run():
    today = get_today_date()
    RAW_EMAIL = os.environ.get("EMAIL")
    RAW_PASSWORD = os.environ.get("PASSWORD")
    NOTIFY_EMAIL = sanitize_email(os.environ.get("NOTIFY_EMAIL", "t.v.malathi2001@gmail.com"))

    if not RAW_EMAIL or not RAW_PASSWORD:
        err_title = "Missing Credentials Secret"
        err_msg = "EMAIL or PASSWORD environment variables are missing from GitHub Repository Secrets."
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

    # Connect to SMTP with retry mechanism for transient network issues
    connection = None
    max_retries = 3
    auth_failed = False

    for attempt in range(1, max_retries + 1):
        try:
            print(f"Connecting to Gmail SMTP server (Attempt {attempt}/{max_retries})...")
            connection = smtplib.SMTP("smtp.gmail.com", 587, timeout=30)
            connection.starttls()
            connection.login(MY_EMAIL, MY_PASSWORD)
            print("SMTP Authentication successful!")
            break
        except smtplib.SMTPAuthenticationError as auth_err:
            auth_failed = True
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
            
            emit_github_annotation(err_title, f"Gmail rejected login for {MY_EMAIL}. Please update your PASSWORD secret in GitHub Repository Secrets.")
            
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
            break
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

            msg = EmailMessage()
            msg["From"] = MY_EMAIL
            msg["To"] = recipient_email
            msg["Subject"] = "Happy Birthday! 🎉"
            msg.set_content(contents)

            try:
                connection.send_message(msg)
                print(f"Email sent successfully to {name} <{recipient_email}>")
                successful_wishes.append(f"{name} ({recipient_email})")
            except Exception as send_err:
                print(f"ERROR sending email to {name} <{recipient_email}>: {send_err}")
                failed_wishes.append(f"{name} ({recipient_email}) - Error: {send_err}")

        # Forward/Notify email feature: Notify NOTIFY_EMAIL about today's birthdays
        if NOTIFY_EMAIL:
            print(f"Sending today's birthday notification summary email to {NOTIFY_EMAIL}...")
            notify_msg = EmailMessage()
            notify_msg["From"] = MY_EMAIL
            notify_msg["To"] = NOTIFY_EMAIL
            notify_msg["Subject"] = f"🎂 Today's Birthday Alert: {today.strftime('%d %B %Y')}"

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
            
            notify_msg.set_content("\n".join(body_lines))

            try:
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


if __name__ == "__main__":
    run()