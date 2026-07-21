import base64
import os
import sys

data = os.environ.get("BIRTHDAYS_CSV", "").strip()

if not data:
    # Check fallback 1: secret.txt
    if os.path.exists("secret.txt"):
        print("BIRTHDAYS_CSV env var is empty. Reading from local secret.txt...")
        with open("secret.txt", "r", encoding="utf-8") as f:
            data = f.read().strip()
    # Check fallback 2: birthdays.csv already exists
    elif os.path.exists("birthdays.csv"):
        print("BIRTHDAYS_CSV env var is empty, but birthdays.csv already exists. Using existing file.")
        sys.exit(0)

if not data:
    print("ERROR: BIRTHDAYS_CSV environment variable is empty and no fallback file (secret.txt / birthdays.csv) was found.")
    print("Please set BIRTHDAYS_CSV_DATA or BIRTHDAYS_CSV in GitHub Repository Secrets or Variables.")
    sys.exit(1)

print(f"Data length: {len(data)}")

# Determine if data is plain CSV or Base64 encoded
if "name,email" in data or "month,day" in data or "\n" in data:
    print("Detected plain CSV data.")
    csv_content = data
else:
    try:
        csv_content = base64.b64decode(data).decode("utf-8")
        print(f"Successfully decoded base64 data ({csv_content.count(chr(10))} lines).")
    except Exception as e:
        print(f"Base64 decode warning ({e}), falling back to raw data.")
        csv_content = data

with open("birthdays.csv", "w", encoding="utf-8") as f:
    f.write(csv_content)

print("birthdays.csv updated successfully!")