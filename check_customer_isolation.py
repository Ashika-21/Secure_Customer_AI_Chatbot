
import json
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8000"


def post_json(path, data, token=None):
    headers = {"Content-Type": "application/json"}

    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        BASE_URL + path,
        data=json.dumps(data).encode("utf-8"),
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(request) as response:
            body = response.read().decode()
            return response.status, json.loads(body)
    except urllib.error.HTTPError as error:
        body = error.read().decode()
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            pass
        return error.code, body


def get_data(path, token):
    request = urllib.request.Request(
        BASE_URL + path,
        headers={"Authorization": f"Bearer {token}"}
    )

    try:
        with urllib.request.urlopen(request) as response:
            print("HTTP Status:", response.status)
            print("Response:", response.read().decode())
    except urllib.error.HTTPError as error:
        print("HTTP Status:", error.code)
        print("Response:", error.read().decode())


print(" SECURE CUSTOMER AI CHATBOT")
print("----------------------------------")

conversation_id = input("Enter Arun's conversation ID: ").strip()

phone = input("Enter Deepa's registered phone number: ").strip()

print("\nRequesting OTP for Deepa...")
status, result = post_json(
    "/auth/request-otp",
    {"phone": phone}
)
print("OTP request status:", status)
print("Response:", result)

if status != 200:
    print("OTP request failed. Check the response above.")
    raise SystemExit

print("\nCheck the Uvicorn terminal for Deepa's development OTP.")
otp = input("Enter Deepa's 6-digit OTP: ").strip()

status, result = post_json(
    "/auth/verify-otp",
    {"phone": phone, "otp": otp}
)

if status != 200:
    print("Deepa login failed.")
    print("HTTP Status:", status)
    print("Response:", result)
    raise SystemExit

deepa_token = result["access_token"]
print("\nDeepa login successful.")

print("\nTrying to access Arun's conversation as Deepa...")
get_data(
    f"/conversations/{conversation_id}/messages",
    deepa_token
)