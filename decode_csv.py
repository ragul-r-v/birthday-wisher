import base64
import os

data = os.environ["BIRTHDAYS_CSV"]
decoded = base64.b64decode(data).decode("utf-8")

with open("birthdays.csv", "w") as f:
    f.write(decoded)

print(f"Lines written: {decoded.count(chr(10))}")