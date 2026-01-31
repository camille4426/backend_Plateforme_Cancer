import requests
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_auth():
    print("Testing Authentication Flow...")
    
    # 1. Login (Get Token)
    print("\n[1] Testing Login (POST /token)...")
    try:
        resp = requests.post(f"{BASE_URL}/token", data={"username": "admin", "password": "admin"})
        if resp.status_code == 200:
            token = resp.json().get("access_token")
            print(f"✅ Login Successful. Token: {token[:20]}...")
        else:
            print(f"❌ Login Failed: {resp.status_code} - {resp.text}")
            return
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return

    # 2. Test Protected Route without Token
    print("\n[2] Testing Protected Route WITHOUT Token (GET /spectrum/0/0/0)...")
    resp = requests.get(f"{BASE_URL}/spectrum/0/0/0")
    if resp.status_code == 401:
        print("✅ Access Denied as expected (401).")
    else:
        print(f"❌ Unexpected Status: {resp.status_code}")

    # 3. Test Protected Route WITH Token
    print("\n[3] Testing Protected Route WITH Token (GET /spectrum/0/0/0)...")
    # Note: This might fail if no MRSI data is loaded, but it should return 200 or 500/404, NOT 401.
    # Actually, controller checks `if self.last_mrsi is None`.
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{BASE_URL}/spectrum/0/0/0", headers=headers)
    
    if resp.status_code == 401:
        print("❌ Access Denied even with token.")
    else:
        print(f"✅ Access Granted (Status: {resp.status_code}). Auth middleware working.")

if __name__ == "__main__":
    test_auth()
