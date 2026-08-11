import os
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

# Ensure timezone is IST (Asia/Kolkata) matching the workflow schedule (~6:00 AM IST)
try:
    from zoneinfo import ZoneInfo
    today = datetime.now(ZoneInfo("Asia/Kolkata"))
except Exception:
    today = datetime.now()

MY_EMAIL = os.environ.get("EMAIL")
MY_PASSWORD = os.environ.get("PASSWORD")
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL", "t.v.malathi2001@gmail.com").strip()

if not MY_EMAIL or not MY_PASSWORD:
    print("ERROR: EMAIL or PASSWORD environment variables are missing from secrets.")
    sys.exit(1)

MY_EMAIL = MY_EMAIL.strip().strip("'\"")
# App passwords can contain spaces (e.g. "abcd efgh ijkl mnop"); remove spaces and outer quotes
MY_PASSWORD = MY_PASSWORD.strip().strip("'\"").replace(" ", "")

print(f"Running Birthday Wisher for date: {today.strftime('%Y-%m-%d')} (Month: {today.month}, Day: {today.day})")

if not os.path.exists("birthdays.csv"):
    print("ERROR: birthdays.csv file not found!")
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

try:
    with smtplib.SMTP("smtp.gmail.com", 587) as connection:
        connection.starttls()
        connection.login(MY_EMAIL, MY_PASSWORD)

        successful_wishes = []
        failed_wishes = []

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

except smtplib.SMTPAuthenticationError as auth_err:
    print(f"\nERROR: SMTP Authentication Failed (535 Bad Credentials): {auth_err}")
    print("\nTroubleshooting Steps:")
    print("1. Go to your Google Account (Security -> 2-Step Verification -> App Passwords).")
    print("2. Generate a new App Password for 'Mail'.")
    print("3. Go to GitHub Repository -> Settings -> Secrets and variables -> Actions.")
    print("4. Update the 'PASSWORD' secret with your new 16-character App Password.")
    sys.exit(1)
except Exception as e:
    print(f"ERROR sending email via SMTP: {e}")
    sys.exit(1)