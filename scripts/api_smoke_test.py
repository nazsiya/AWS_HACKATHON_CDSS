import urllib.request
import urllib.error
import urllib.parse
import json

base_url = "https://b1q9qcuqia.execute-api.ap-south-1.amazonaws.com/dev"

def test_endpoint(path):
    url = f"{base_url}{path}"
    print(f"Testing {url}...")
    req = urllib.request.Request(url)
    try:
        response = urllib.request.urlopen(req)
        print(f"Status: {response.status}")
        print(f"Body: {response.read().decode('utf-8')[:200]}")
    except urllib.error.HTTPError as e:
        print(f"HTTPError: {e.code} - {e.reason}")
        print(f"Body: {e.read().decode('utf-8')[:500]}")
    except Exception as e:
        print(f"Error: {e}")

test_endpoint("/health")
# Preflight test
req = urllib.request.Request(f"{base_url}/api/v1/patients", method="OPTIONS")
req.add_header("Origin", "http://localhost:5174")
req.add_header("Access-Control-Request-Method", "GET")
try:
    response = urllib.request.urlopen(req)
    print(f"OPTIONS Status: {response.status}")
    print("Headers:")
    for key, value in response.headers.items():
        if key.lower().startswith('access-control'):
            print(f"  {key}: {value}")
except Exception as e:
    print(f"OPTIONS Error: {e}")
