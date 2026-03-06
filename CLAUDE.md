# CLAUDE.md — Logographic Chat

## Project Overview

A networked TUI chat application with two components:

1. Backend — Django web server. Manages users, rooms, messages, authentication (including Apple/Google
   OAuth). Exposes REST + WebSocket APIs.
2. Client — Python TUI (distributed via Homebrew). Connects to the hosted backend. No local database, no ORM, no Django
   dependency.

```
logographic-chat/
├── backend/                  # Django project (hosted by you)
│   ├── manage.py
│   ├── logographic_chat/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── asgi.py
│   │   └── wsgi.py
│   ├── chat/                 # Core chat app
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── consumers.py     # WebSocket consumers
│   │   └── routing.py
│   ├── accounts/             # Auth + device flow
│   │   ├── models.py
│   │   ├── views.py
│   │   └── urls.py
│   ├── templates/
│   │   └── accounts/
│   │       ├── verify_device.html
│   │       └── auth_success.html
│   └── requirements.txt
├── client/                   # TUI client (distributed via Homebrew)
│   ├── pyproject.toml
│   ├── src/
│   │   └── logographic_chat/
│   │       ├── __init__.py
│   │       ├── cli.py        # Entry point
│   │       ├── auth.py       # Device auth flow
│   │       ├── api.py        # REST client
│   │       ├── ws.py         # WebSocket client
│   │       └── tui.py        # Textual UI
│   └── build/
│       └── logographic-chat.rb  # Homebrew formula
└── CLAUDE.md                 # This file
```

## Part 1: Backend

### 1.1 Dependencies

```python
# backend / requirements.txt
django >= 5.1
django - channels[daphne] >= 4.0
djangorestframework >= 3.15
django - allauth[socialaccount] >= 65.0
channels - redis >= 4.2
djangorestframework - simplejwt >= 5.3
psycopg[binary] >= 3.2
```

### 1.2 Settings Scaffold

```python 
# backend/config/settings.py

INSTALLED_APPS = [
    "daphne",  # Must be first for ASGI
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # Third-party
    "rest_framework",
    "channels",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.apple",
    "allauth.socialaccount.providers.google",
    # Local
    "accounts",
    "chat",
]

SITE_ID = 1

# Channel layers — use Redis in production
if DEBUG:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [
                    os.getenv("REDIS_URL", "redis://localhost:6379")
                ],
            },
        },
    }
else:
    # For in-memory (development only)
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

DATABASES = {
    "default": dj_database_url.config(
        default="sqlite:///" + str(BASE_DIR / "db.sqlite3"),
        conn_max_age=600,
    )
}

ASGI_APPLICATION = "config.asgi.application"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_AUTHENTICATION_METHOD = "username_email"
ACCOUNT_EMAIL_VERIFICATION = "optional"
LOGIN_REDIRECT_URL = "/auth/device/success/"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
```

### 1.3 ASGI Configuration

```python 
# backend/config/asgi.py
import os
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django_asgi = get_asgi_application()

from chat.routing import websocket_urlpatterns
from chat.middleware import JWTAuthMiddleware

application = ProtocolTypeRouter({
    "http": django_asgi,
    "websocket": AllowedHostsOriginValidator(
        JWTAuthMiddleware(URLRouter(websocket_urlpatterns))
    ),
})
```

### 1.4 Chat Models

```python 
# backend/chat/models.py
from django.conf import settings
from django.db import models


class Room(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Message(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="messages")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="messages"
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user.username}: {self.content[:50]}"
  ```

> Note: Don't create a custom User model. Use Django's built-in auth.User via settings.AUTH_USER_MODEL. allauth extends
> it for you.

### 1.5 Device Auth models

```python 
# backend/accounts/models.py
import secrets
from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta


def generate_device_code():
    return secrets.token_urlsafe(32)


def generate_user_code():
    return secrets.token_urlsafe(4).upper()[:8]


def default_expiry():
    return timezone.now() + timedelta(minutes=15)


class DeviceCode(models.Model):
    device_code = models.CharField(max_length=64, unique=True, default=generate_device_code)
    user_code = models.CharField(max_length=8, unique=True, default=generate_user_code)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_expiry)
    is_authorized = models.BooleanField(default=False)

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
```

### 1.6 Device Auth Endpoints

```python 
# backend/accounts/views.py
from django.shortcuts import render, get_object_or_404, redirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from .models import DeviceCode


@api_view(["POST"])
@permission_classes([AllowAny])
def device_request(request):
    """CLI calls this to start the auth flow."""
    dc = DeviceCode.objects.create()
    return Response({
        "device_code": dc.device_code,
        "user_code": dc.user_code,
        "verification_url": f"{request.scheme}://{request.get_host()}/auth/device/verify/",
        "expires_in": 900,
        "interval": 5,
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def device_token(request):
    """CLI polls this until the user authorizes in the browser."""
    device_code = request.data.get("device_code")
    try:
        dc = DeviceCode.objects.get(device_code=device_code)
    except DeviceCode.DoesNotExist:
        return Response({"error": "invalid_device_code"}, status=400)

    if dc.is_expired:
        return Response({"error": "expired_token"}, status=400)

    if not dc.is_authorized or dc.user is None:
        return Response({"error": "authorization_pending"}, status=428)

    refresh = RefreshToken.for_user(dc.user)
    username = dc.user.username
    dc.delete()  # Single use
    return Response({
        "access_token": str(refresh.access_token),
        "refresh_token": str(refresh),
        "username": username,
    })


def device_verify(request):
    """Browser page where user enters their user_code then logs in."""
    if request.method == "GET":
        code = request.GET.get("code", "")
        return render(request, "accounts/verify_device.html", {"code": code})

    if request.method == "POST":
        user_code = request.POST.get("user_code", "").strip().upper()
        try:
            dc = DeviceCode.objects.get(user_code=user_code)
        except DeviceCode.DoesNotExist:
            return render(request, "accounts/verify_device.html", {"error": "Invalid code."})

        if dc.is_expired:
            return render(request, "accounts/verify_device.html", {
                "error": "Code expired. Try again from the terminal."
            })

        if not request.user.is_authenticated:
            request.session["pending_device_code"] = user_code
            return redirect(f"/accounts/login/?next=/auth/device/verify/?code={user_code}")

        dc.user = request.user
        dc.is_authorized = True
        dc.save()
        return render(request, "accounts/auth_success.html")
```

### 1.7 URL Wiring

```python 
# backend/accounts/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("api/auth/device/", views.device_request),
    path("api/auth/token/", views.device_token),
    path("auth/device/verify/", views.device_verify),
]
```

```python 
# backend/config/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("", include("accounts.urls")),
    path("api/", include("chat.urls")),
]
```

### 1.8 Chat REST API

```python 
# backend/chat/serializers.py
from rest_framework import serializers
from .models import Room, Message


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ["id", "name", "created_at"]


class MessageSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Message
        fields = ["id", "username", "content", "created_at"]
```

```python 
# backend/chat/views.py
from rest_framework import generics
from .models import Room, Message
from .serializers import RoomSerializer, MessageSerializer


class RoomListView(generics.ListAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer


class MessageListView(generics.ListAPIView):
    serializer_class = MessageSerializer

    def get_queryset(self):
        return Message.objects.filter(
            room_id=self.kwargs["room_id"]
        ).select_related("user").order_by("-created_at")[:50]
```

```python 
# backend/chat/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("rooms/", views.RoomListView.as_view()),
    path("rooms/<int:room_id>/messages/", views.MessageListView.as_view()),
]
```

### 1.9 WebSocket Consumer

```python 
# backend/chat/consumers.py
import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Room, Message


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.group_name = f"chat_{self.room_id}"
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close()
            return
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content):
        message_text = content.get("message", "").strip()
        if not message_text:
            return
        msg = await self.save_message(message_text)
        await self.channel_layer.group_send(self.group_name, {
            "type": "chat.message",
            "message": message_text,
            "username": self.user.username,
            "created_at": msg.created_at.isoformat(),
        })

    async def chat_message(self, event):
        await self.send_json({
            "username": event["username"],
            "message": event["message"],
            "created_at": event["created_at"],
        })

    @database_sync_to_async
    def save_message(self, content):
        return Message.objects.create(room_id=self.room_id, user=self.user, content=content)
```

### 1.10 WebSocket Routing + JWT Middleware

```python 
# backend/chat/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<room_id>\d+)/$", consumers.ChatConsumer.as_asgi()),
]
```

```python 
# backend/chat/middleware.py
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model

User = get_user_model()


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query = dict(
            x.split("=") for x in scope["query_string"].decode().split("&") if "=" in x
        )
        token = query.get("token")
        scope["user"] = await self.get_user(token) if token else AnonymousUser()
        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def get_user(self, raw_token):
        try:
            validated = AccessToken(raw_token)
            return User.objects.get(id=validated["user_id"])
        except Exception:
            return AnonymousUser()
```

### 1.11 Minimal Templates

```html
<!-- backend/templates/accounts/verify_device.html -->
<!DOCTYPE html>
<html>
<head><title>Logographic Chat — Authorize Device</title></head>
<body>
<h1>Authorize your terminal</h1>
{% if error %}<p style="color:red">{{ error }}</p>{% endif %}
<form method="post">
    {% csrf_token %}
    <label>Enter the code shown in your terminal:</label><br>
    <input name="user_code" value="{{ code }}" maxlength="8"
           style="font-size:2em; letter-spacing:0.3em; text-transform:uppercase;" autofocus>
    <button type="submit">Authorize</button>
</form>
<p>Don't have an account? <a href="/accounts/signup/">Sign up</a></p>
</body>
</html>
```

```html 
<!-- backend/templates/accounts/auth_success.html -->
<!DOCTYPE html>
<html>
<head><title>Logographic Chat — Authorized</title></head>
<body>
<h1>You're in.</h1>
<p>Your terminal has been authorized. You can close this tab.</p>
</body>
</html>
```

## Part 2: TUI Client

### 2.1 Project Config

```toml
# client/pyproject.toml
[project]
name = "logographic-chat"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "textual>=0.80",
    "httpx>=0.27",
    "websockets>=13.0",
    "click>=8.1",
]

[project.scripts]
logographic-chat = "logographic_chat.cli:main"
```

### 2.2 Auth Module (Device Flow)

```python
# client/src/logographic_chat/auth.py
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
```

### 2.3 REST API Client

```python 
# client/src/logographic_chat/api.py
import httpx


class ChatAPI:
    def __init__(self, server_url: str, access_token: str):
        self.client = httpx.Client(
            base_url=server_url,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    def list_rooms(self) -> list[dict]:
        resp = self.client.get("/api/rooms/")
        resp.raise_for_status()
        return resp.json()

    def get_messages(self, room_id: int, limit: int = 50) -> list[dict]:
        resp = self.client.get(f"/api/rooms/{room_id}/messages/")
        resp.raise_for_status()
        return resp.json()

    def verify_token(self) -> bool:
        try:
            self.list_rooms()
            return True
        except httpx.HTTPStatusError:
            return False
```

### 2.4 Websocket Client

```python 
# client/src/logographic_chat/ws.py
import json
import websockets


class ChatSocket:
    def __init__(self, server_url: str, access_token: str):
        ws_scheme = "wss" if server_url.startswith("https") else "ws"
        host = server_url.replace("https://", "").replace("http://", "")
        self.base_ws_url = f"{ws_scheme}://{host}"
        self.token = access_token
        self.ws = None

    async def connect(self, room_id: int):
        url = f"{self.base_ws_url}/ws/chat/{room_id}/?token={self.token}"
        self.ws = await websockets.connect(url)

    async def send(self, message: str):
        await self.ws.send(json.dumps({"message": message}))

    async def receive(self):
        return json.loads(await self.ws.recv())

    async def close(self):
        if self.ws:
            await self.ws.close()
```

### 2.5 TUI (Textual)

```python 
# client/src/logographic_chat/tui.py
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Header, Footer, Input, Static
from .api import ChatAPI
from .ws import ChatSocket


class MessageView(Static):
    def __init__(self, username: str, content: str, **kwargs):
        super().__init__(**kwargs)
        self.username = username
        self.content = content

    def render(self):
        return f"[bold]{self.username}[/bold]  {self.content}"


class ChatApp(App):
    CSS = """
    #messages { height: 1fr; }
    #input { dock: bottom; }
    """
    BINDINGS = [("escape", "quit", "Quit")]

    def __init__(self, server_url: str, access_token: str, username: str):
        super().__init__()
        self.server_url = server_url
        self.access_token = access_token
        self.username = username
        self.api = ChatAPI(server_url, access_token)
        self.socket = ChatSocket(server_url, access_token)
        self.current_room_id = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield VerticalScroll(id="messages")
        yield Input(placeholder="Type a message...", id="input")
        yield Footer()

    async def on_mount(self):
        rooms = self.api.list_rooms()
        if not rooms:
            self.query_one("#messages").mount(MessageView("system", "No rooms available."))
            return
        self.current_room_id = rooms[0]["id"]
        self.title = f"# {rooms[0]['name']}"

        messages = self.api.get_messages(self.current_room_id)
        container = self.query_one("#messages")
        for msg in messages:
            await container.mount(MessageView(msg["username"], msg["content"]))

        await self.socket.connect(self.current_room_id)
        self.run_worker(self.listen_for_messages())

    async def listen_for_messages(self):
        try:
            while True:
                data = await self.socket.receive()
                container = self.query_one("#messages")
                await container.mount(MessageView(data["username"], data["message"]))
                container.scroll_end()
        except Exception:
            pass

    async def on_input_submitted(self, event: Input.Submitted):
        text = event.value.strip()
        if text and self.socket:
            await self.socket.send(text)
            event.input.value = ""
```

### 2.6 CLI Entry Point

```python
# client/src/logographic_chat/cli.py
import click

DEFAULT_SERVER = "https://chat.codebylevel.com"


def handle_main_tui(server):
    """Handle the actual TUI functionality in a separate function."""
    from logographic_chat.auth import load_credentials, device_login, refresh_access_token, debug, error

    debug("CLI starting", server=server)
    creds = load_credentials()
    if not creds:
        click.echo("Welcome to Logographic Chat!")
        click.echo("You need to sign in first.\n")
        creds = device_login(server)
    else:
        debug("Found stored credentials, attempting refresh")
        refreshed = refresh_access_token(server)
        if refreshed:
            creds = refreshed
        else:
            click.echo("Session expired. Please sign in again.\n")
            creds = device_login(server)

    debug("Launching TUI", server=server, username=creds["username"])
    try:
        from logographic_chat.tui import ChatApp
        app = ChatApp(server_url=server, access_token=creds["access_token"], username=creds["username"])
        app.run()
    except Exception as e:
        error("TUI crashed", error=str(e))
        raise


@click.group(invoke_without_command=True)
@click.option("--server", default=DEFAULT_SERVER, envvar="LOGOGRAPHIC_SERVER")
@click.pass_context
def main(ctx, server):
    """Logographic Chat — a TUI chat client."""
    ctx.ensure_object(dict)
    ctx.obj["server"] = server
    if ctx.invoked_subcommand is not None:
        return

    # Only load async dependencies when actually running the TUI
    handle_main_tui(server)


@main.command()
@click.option("--server", default=DEFAULT_SERVER, envvar="LOGOGRAPHIC_SERVER")
@click.pass_context
def login(ctx, server):
    """Authenticate with the server."""
    from logographic_chat.auth import device_login
    device_login(server)


@main.command()
def logout():
    """Remove stored credentials."""
    from logographic_chat.auth import clear_credentials
    clear_credentials()
    click.echo("Logged out.")


if __name__ == "__main__":
    main()
```

## Part 3: Homebrew Distribution

This is a CLI binary, so it uses a **Formula** (not a Cask — Casks are for GUI `.app` bundles and DMGs).
The formula lives in a separate tap repo: `github.com/ike5/homebrew-logographic-chat`.

### 3.1 Build Configuration

**PyInstaller Spec File (`client/logographic-chat.spec`)**
```python
# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['src/logographic_chat/cli.py'],
    pathex=['src'],
    binaries=[],
    datas=[],
    hiddenimports=['click', 'httpx', 'websockets', 'textual'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='logographic-chat',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

**Key Configuration Notes:**
- Use `pathex=['src']` to include the source code directory
- Include explicit `hiddenimports` for all async dependencies
- Ensure `if __name__ == "__main__":` block exists in CLI entry point
- Move Textual/async imports inside functions to avoid loading them for simple commands

### 3.2 Build Process

```bash
cd client/
pip install pyinstaller textual httpx websockets click
pyinstaller logographic-chat.spec
# Output: dist/logographic-chat
```

Build for each target in CI (GitHub Actions): darwin-arm64 (macOS 14 runner), linux-x86_64 (Ubuntu).
macOS x86_64 is dropped — GitHub no longer provides Intel Mac runners.

### 3.3 Package as Tarballs

Homebrew expects a tarball, not a raw binary. After each PyInstaller build, wrap it:

```bash
# macOS arm64
tar -czf logographic-chat-darwin-arm64.tar.gz logographic-chat

# Linux x86_64
tar -czf logographic-chat-linux-x86_64.tar.gz logographic-chat
```

Upload the `.tar.gz` files as GitHub Release assets.

### 3.4 Compute SHA256 Hashes

```bash
shasum -a 256 logographic-chat-darwin-arm64.tar.gz
shasum -a 256 logographic-chat-linux-x86_64.tar.gz
```

Real SHA256 values are required — Homebrew will reject `PLACEHOLDER`.

### 3.4 Tap Repo Structure

The tap repo must be named `homebrew-logographic-chat` and structured as:

```
homebrew-logographic-chat/
└── Formula/
    └── logographic-chat.rb
```

### 3.5 Homebrew Formula

```rb
# Formula/logographic-chat.rb  (in github.com/ike5/homebrew-logographic-chat)
class LogographicChat < Formula
  desc "TUI chat client for Logographic Chat"
  homepage "https://github.com/ike5/logographic-chat"
  version "0.1.0"
  license "MIT"

  on_macos do
    url "https://github.com/ike5/logographic-chat/releases/download/v0.1.0/logographic-chat-darwin-arm64.tar.gz"
    sha256 "REAL_SHA256_HERE"
  end

  on_linux do
    url "https://github.com/ike5/logographic-chat/releases/download/v0.1.0/logographic-chat-linux-x86_64.tar.gz"
    sha256 "REAL_SHA256_HERE"
  end

  def install
    bin.install "logographic-chat"
  end

  test do
    # Must not require network — --help is safe in Homebrew's sandbox
    assert_match "Usage", shell_output("#{bin}/logographic-chat --help")
  end
end
```

### 3.6 Tap and Install

```bash
brew tap ike5/logographic-chat
brew install logographic-chat
```

Local testing before publishing:

```bash
brew install --build-from-source ./Formula/logographic-chat.rb
brew audit --strict --new-formula logographic-chat
```

## Part 4: Deployment Checklist

Backend: PostgreSQL provisioned, Redis running, ALLOWED_HOSTS/CORS configured, DJANGO_SECRET_KEY from env, Google +
Apple OAuth creds in allauth admin, HTTPS enforced, migrations run, superuser created, initial rooms seeded, deployed
with Daphne behind nginx.

Client: PyInstaller builds for all targets in CI, release assets uploaded, SHA256s in formula updated, brew install
tested on clean machine, full auth flow verified end-to-end.

---

### Design Decisions

No Django on the client. The TUI has no database, no migrations, no admin. Shipping Django would add ~30MB for zero
benefit.

JWT over session auth. Sessions need cookies, which don't work in CLI. JWTs are self-contained, stateless on the client,
trivial to include in REST headers and WebSocket query strings.

Device flow over local redirect. RFC 8628 device flow avoids spinning up a local HTTP server on the user's machine (port
conflicts, firewalls). It's what GitHub CLI uses.

Textual for TUI. Modern, async-native, CSS-like styling, actively maintained. The alternatives (urwid, curses) are
lower-level for no benefit here.

Account deletion web-only. User visits the Django site, deletes account. Next CLI auth attempt fails, CLI prompts for
re-auth. No client-side deletion logic needed.
