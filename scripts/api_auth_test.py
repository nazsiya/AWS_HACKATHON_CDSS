import urllib.request
import urllib.error
import urllib.parse
import json
import os
import subprocess

# Use env for credentials (do not commit). Set COGNITO_USER_POOL_ID, COGNITO_CLIENT_ID, COGNITO_TEST_USERNAME, COGNITO_TEST_PASSWORD.
user_pool_id = os.environ.get("COGNITO_USER_POOL_ID", "").strip()
client_id = os.environ.get("COGNITO_CLIENT_ID", "").strip()
username = os.environ.get("COGNITO_TEST_USERNAME", "").strip()
password = os.environ.get("COGNITO_TEST_PASSWORD", "").strip()
if not all([user_pool_id, client_id, username, password]):
    print("Set COGNITO_USER_POOL_ID, COGNITO_CLIENT_ID, COGNITO_TEST_USERNAME, COGNITO_TEST_PASSWORD (do not commit).")
    exit(1)

# 1. Get Cognito token
print("Getting Cognito token...")
result = subprocess.run([
    "python", "scripts/auth/get_token.py",
    "--user-pool-id", user_pool_id,
    "--client-id", client_id,
    "--username", username,
    "--password", password,
], capture_output=True, text=True)

if result.returncode != 0:
    print(f"Failed to get token: {result.stderr}")
    exit(1)

token = result.stdout.strip()
print(f"Token length: {len(token)}")

base_url = os.environ.get("API_BASE_URL", "https://b1q9qcuqia.execute-api.ap-south-1.amazonaws.com/dev")

def test_endpoint(path):
    url = f"{base_url}{path}"
    print(f"\nTesting GET {url}...")
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    try:
        response = urllib.request.urlopen(req)
        print(f"Status: {response.status}")
        print(f"Body: {response.read().decode('utf-8')[:200]}")
    except urllib.error.HTTPError as e:
        print(f"HTTPError: {e.code} - {e.reason}")
        print(f"Body: {e.read().decode('utf-8')[:500]}")
    except Exception as e:
        print(f"Error: {e}")

test_endpoint("/api/v1/surgeries")
test_endpoint("/api/v1/patients")
test_endpoint("/dashboard")
