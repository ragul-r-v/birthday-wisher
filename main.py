import os
from datetime import datetime
import pandas
import random
import smtplib
import sys

# Ensure timezone is IST (Asia/Kolkata) matching the workflow schedule (7:00 AM IST)
try:
    from zoneinfo import ZoneInfo
    today = datetime.now(ZoneInfo("Asia/Kolkata"))
except Exception:
    today = datetime.now()

MY_EMAIL = os.environ.get("EMAIL")
MY_PASSWORD = os.environ.get("PASSWORD")

if not MY_EMAIL or not MY_PASSWORD:
    print("ERROR: EMAIL or PASSWORD environment variables are missing from secrets.")
    sys.exit(1)

print(f"Running Birthday Wisher for date: {today.strftime('%Y-%m-%d')} (Month: {today.month}, Day: {today.day})")

if not os.path.exists("birthdays.csv"):
    print("ERROR: birthdays.csv file not found!")
    sys.exit(1)

data = pandas.read_csv("birthdays.csv")

# Find all matching birthdays
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

        for index, birthday_person in birthday_people.iterrows():
            file_path = f"letter_templates/letter_{random.randint(1, 3)}.txt"

            with open(file_path, "r", encoding="utf-8") as letter_file:
                contents = letter_file.read()
                contents = contents.replace("[NAME]", str(birthday_person["name"]).strip())

            msg = f"From: {MY_EMAIL}\nTo: {birthday_person['email']}\nSubject: Happy Birthday!\n\n{contents}"

            connection.sendmail(
                from_addr=MY_EMAIL,
                to_addrs=birthday_person["email"],
                msg=msg.encode("utf-8")
            )

            print(f"Email sent successfully to {birthday_person['name']} <{birthday_person['email']}>")

except Exception as e:
    print(f"ERROR sending email via SMTP: {e}")
    sys.exit(1)