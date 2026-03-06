import json
import time
import webbrowser
from datetime import datetime
from pathlib import Path

import httpx

CONFIG_DIR = Path.home() / ".config" / "logographic-chat"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"
LOG_FILE = CONFIG_DIR / "debug.log"


def log(level: str, msg: str, **kwargs):
    """Write to both stdout and log file."""
    timestamp = datetime.now().isoformat(timespec="seconds")
    log_entry = f"[{timestamp}] [{level}] {msg}"
    if kwargs:
        log_entry += f" | {kwargs}"
    print(log_entry, flush=True)
    # Also write to log file
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(log_entry + "\n")


def debug(msg: str, **kwargs):
    log("DEBUG", msg, **kwargs)


def info(msg: str, **kwargs):
    log("INFO", msg, **kwargs)


def error(msg: str, **kwargs):
    log("ERROR", msg, **kwargs)


def load_credentials():
    if CREDENTIALS_FILE.exists():
        debug("Credentials file found")
        return json.loads(CREDENTIALS_FILE.read_text())
    debug("No credentials file found")
    return None


def save_credentials(data):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_FILE.write_text(json.dumps(data, indent=2))
    CREDENTIALS_FILE.chmod(0o600)


def clear_credentials():
    CREDENTIALS_FILE.unlink(missing_ok=True)


def refresh_access_token(server_url: str) -> dict | None:
    """Try to get a new access token using the stored refresh token. Returns updated creds or None."""
    creds = load_credentials()
    if not creds or "refresh_token" not in creds:
        debug("No refresh token available")
        return None
    try:
        debug("Attempting token refresh", server=server_url)
        with httpx.Client(base_url=server_url) as client:
            resp = client.post("/api/token/refresh/", json={"refresh": creds["refresh_token"]})
            debug("Token refresh response", status=resp.status_code)
            if resp.status_code == 200:
                creds["access_token"] = resp.json()["access"]
                save_credentials(creds)
                info("Token refresh successful")
                return creds
            else:
                error("Token refresh failed", status=resp.status_code, body=resp.text[:200])
    except Exception as e:
        error("Token refresh exception", error=str(e))
    return None


def device_login(server_url: str) -> dict:
    info("Starting device login flow", server=server_url)
    debug("Creating HTTP client")
    with httpx.Client(base_url=server_url, timeout=30.0) as client:
        debug("Calling /api/auth/device/")
        resp = client.post("/api/auth/device/")
        debug("Device request response", status=resp.status_code)
        resp.raise_for_status()
        data = resp.json()

        device_code = data["device_code"]
        user_code = data["user_code"]
        verify_url = data["verification_url"]
        interval = data.get("interval", 5)
        expires_in = data.get("expires_in", 900)  # Default 15 minutes

        full_url = f"{verify_url}?code={user_code}"
        print(f"\nYour code: {user_code}")
        print(f"Opening {full_url} ...")
        webbrowser.open(full_url)
        print("Waiting for you to authorize in the browser...\n")
        print("You have", expires_in // 60, "minutes to complete authentication.")

        # Add timeout mechanism
        import time
        start_time = time.time()

        while True:
            # Check if timeout exceeded
            elapsed = time.time() - start_time
            if elapsed > expires_in:
                error("Login timeout exceeded")
                raise SystemExit("Authentication timeout. Please try again.")

            time.sleep(interval)
            debug("Polling /api/auth/token/")
            try:
                resp = client.post("/api/auth/token/", json={"device_code": device_code}, timeout=10.0)
            except httpx.TimeoutException:
                error("Token polling timeout")
                continue  # Retry on network timeout
            except httpx.RequestError as e:
                error("Network error during token polling", error=str(e))
                continue  # Retry on network errors

            debug("Token poll response", status=resp.status_code)
            if resp.status_code == 200:
                creds = resp.json()
                save_credentials(creds)
                print(f"Authenticated as @{creds['username']}")
                info("Login successful", username=creds['username'])
                return creds

            error_msg = resp.json().get("error")
            debug("Token poll error", error=error_msg)
            if error_msg == "authorization_pending":
                continue
            elif error_msg == "expired_token":
                error("Code expired during login")
                raise SystemExit("Code expired. Please try again.")
            else:
                error("Auth error", error=error_msg)
                raise SystemExit(f"Auth error: {error_msg}")
