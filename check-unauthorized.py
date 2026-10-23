
import urllib.request
import urllib.error

url = "http://127.0.0.1:8000/customer/me"
request = urllib.request.Request(url)

try:
    response = urllib.request.urlopen(request)
    print("Unexpected status:", response.status)
except urllib.error.HTTPError as error:
    print("HTTP Status:", error.code)
    print("Response:", error.read().decode())
except urllib.error.URLError:
    print("Cannot connect to the API. Check whether Uvicorn is running.")