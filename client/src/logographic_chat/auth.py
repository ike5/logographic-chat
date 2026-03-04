import json
import time
import webbrowser
from pathlib import Path

import httpx

CONFIG_DIR = Path.home() / ".config" / "logographic-chat"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"


def load_credentials():
    if CREDENTIALS_FILE.exists():
        return json.loads(CREDENTIALS_FILE.read_text())
    return None


def save_credentials(data):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_FILE.write_text(json.dumps(data, indent=2))
    CREDENTIALS_FILE.chmod(0o600)


def clear_credentials():
    CREDENTIALS_FILE.unlink(missing_ok=True)


def device_login(server_url: str) -> dict:
    with httpx.Client(base_url=server_url) as client:
        resp = client.post("/api/auth/device/")
        resp.raise_for_status()
        data = resp.json()

        device_code = data["device_code"]
        user_code = data["user_code"]
        verify_url = data["verification_url"]
        interval = data.get("interval", 5)

        full_url = f"{verify_url}?code={user_code}"
        print(f"\nYour code: {user_code}")
        print(f"Opening {full_url} ...")
        webbrowser.open(full_url)
        print("Waiting for you to authorize in the browser...\n")

        while True:
            time.sleep(interval)
            resp = client.post("/api/auth/token/", json={"device_code": device_code})
            if resp.status_code == 200:
                creds = resp.json()
                save_credentials(creds)
                print(f"Authenticated as @{creds['username']}")
                return creds
            error = resp.json().get("error")
            if error == "authorization_pending":
                continue
            elif error == "expired_token":
                raise SystemExit("Code expired. Please try again.")
            else:
                raise SystemExit(f"Auth error: {error}")
