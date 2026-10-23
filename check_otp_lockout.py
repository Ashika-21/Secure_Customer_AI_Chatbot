
import json
import urllib.request
import urllib.error
from sqlalchemy import select
from database import SessionLocal
from models import Customer

BASE_URL = "http://127.0.0.1:8000"
PHONE = input("Enter registered customer phone number: ").strip()


def post_json(path, data):
    request = urllib.request.Request(
        BASE_URL + path,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(request) as response:
            print("HTTP Status:", response.status)
            print("Response:", response.read().decode())
    except urllib.error.HTTPError as error:
        print("HTTP Status:", error.code)
        print("Response:", error.read().decode())


print("\nStep 1: Request a fresh OTP")
post_json("/auth/request-otp", {"phone": PHONE})

print("\nCheck the Uvicorn terminal for the development OTP.")
print("Do NOT enter the real OTP below.")

for attempt in range(1, 7):
    otp = input(f"\nAttempt {attempt} - Enter wrong 6-digit OTP: ").strip()

    if len(otp) != 6 or not otp.isdigit():
        print("Enter exactly 6 digits. Attempt not sent.")
        continue

    print("Verification result:")
    post_json("/auth/verify-otp", {"phone": PHONE, "otp": otp})

    db = SessionLocal()
    try:
        customer = db.scalar(
            select(Customer).where(Customer.phone == PHONE)
        )
        if customer:
            print("Database attempt counter:", customer.otp_attempts)
            print("OTP expiry:", customer.otp_expires_at)
    finally:
        db.close()