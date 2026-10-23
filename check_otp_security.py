
import json
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8000"

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

phone = input("Enter your registered customer phone number: ").strip()

print("\nRequesting OTP...")
post_json("/auth/request-otp", {"phone": phone})

print("\nEnter exactly 6 digits that are NOT your actual OTP.")
wrong_otp = input("Enter incorrect OTP: ").strip()

if len(wrong_otp) != 6 or not wrong_otp.isdigit():
    print("Please enter exactly 6 digits. Run the test again.")
else:
    print("\nVerifying incorrect OTP...")
    post_json("/auth/verify-otp", {"phone": phone, "otp": wrong_otp})