import os

from datetime import datetime
import pandas
import random
import smtplib

MY_EMAIL = os.environ["EMAIL"]
MY_PASSWORD = os.environ["PASSWORD"]

today = datetime.now()
today_tuple = (today.month, today.day)

data = pandas.read_csv("birthdays.csv")

# Find all matching birthdays
birthday_people = data[
    (data["month"] == today.month) &
    (data["day"] == today.day)
]

for index, birthday_person in birthday_people.iterrows():

    file_path = f"letter_templates/letter_{random.randint(1,3)}.txt"

    with open(file_path) as letter_file:
        contents = letter_file.read()
        contents = contents.replace("[NAME]", birthday_person["name"])

    with smtplib.SMTP("smtp.gmail.com", 587) as connection:
        connection.starttls()
        connection.login(MY_EMAIL, MY_PASSWORD)

        connection.sendmail(
            from_addr=MY_EMAIL,
            to_addrs=birthday_person["email"],
            msg=f"Subject:Happy Birthday!\n\n{contents}"
        )

        print(f"Email sent to {birthday_person['name']}")