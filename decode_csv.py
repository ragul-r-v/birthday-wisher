import base64
import os

data = os.environ.get("BIRTHDAYS_CSV", "")

print(f"Secret length: {len(data)}")
print(f"First 50 chars: {data[:50]}")

if len(data) == 0:
    print("ERROR: Secret is empty!")
    exit(1)

try:
    decoded = base64.b64decode(data).decode("utf-8")
    print(f"Decoded lines: {decoded.count(chr(10))}")
    with open("birthdays.csv", "w") as f:
        f.write(decoded)
    print("CSV written successfully!")
except Exception as e:
    print(f"Decode error: {e}")
    exit(1)