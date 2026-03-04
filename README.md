# Logographic Chat

A networked TUI chat application with a Django backend and Python TUI client.

## Overview

- **Backend**: Django web server with REST + WebSocket APIs, JWT authentication, and device auth flow
- **Client**: Python TUI (Textual) chat client, distributed via Homebrew

## Prerequisites

- Python 3.11+
- PostgreSQL (production) or SQLite (development)
- Redis (for WebSocket channel layers in production)

---

## Backend Setup

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in `backend/`:

```bash
DJANGO_SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# PostgreSQL (production)
DATABASE_URL=postgres://user:pass@localhost:5432/logographic_chat

# Redis (production)
REDIS_URL=redis://localhost:6379

# OAuth (optional - for social login)
SOCIAL_AUTH_APPLE_CLIENT_ID=
SOCIAL_AUTH_APPLE_SECRET=
SOCIAL_AUTH_GOOGLE_CLIENT_ID=
SOCIAL_AUTH_GOOGLE_SECRET=
```

### 3. Run Migrations

```bash
cd backend
python manage.py migrate
```

### 4. Create Superuser

```bash
python manage.py createsuperuser
```

### 5. Start Server

```bash
# Development
python manage.py runserver

# Production with Daphne
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

The backend will be available at `http://localhost:8000`.

### 6. Create Initial Rooms (optional)

```bash
python manage.py shell
```

```python
from chat.models import Room
Room.objects.get_or_create(name="general")
Room.objects.get_or_create(name="random")
```

---

## Client Setup

### 1. Install Dependencies

```bash
cd client
pip install -e .
```

Or install in development mode with dev dependencies:

```bash
pip install -e ".[dev]"
```

### 2. Authentication

Run the client to start the device auth flow:

```bash
logographic-chat --server http://localhost:8000
```

Or explicitly:

```bash
logographic-chat login --server http://localhost:8000
```

This will:
1. Display a device code in the terminal
2. Open your browser to the verification URL
3. Enter the code and log in via Django's authentication system
4. Store credentials locally at `~/.config/logographic-chat/credentials.json`

### 3. Using the Chat

```bash
logographic-chat --server http://localhost:8000
```

**Controls:**
- Type messages and press Enter to send
- Press Escape to quit

---

## Commands

### Backend

```bash
python manage.py migrate          # Run database migrations
python manage.py createsuperuser  # Create admin user
python manage.py runserver       # Start dev server
python manage.py shell            # Django shell
```

### Client

```bash
logographic-chat                  # Start chat (auto-login if credentials exist)
logographic-chat login            # Authenticate with server
logographic-chat logout           # Remove stored credentials
logographic-chat --server URL     # Specify custom server
```

Environment variables:
- `LOGOGRAPHIC_SERVER` - Default server URL

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/device/` | POST | Start device auth flow |
| `/api/auth/token/` | POST | Poll for auth token |
| `/auth/device/verify/` | GET/POST | Device verification page |
| `/api/rooms/` | GET | List chat rooms |
| `/api/rooms/<id>/messages/` | GET | Get room messages |
| `/ws/chat/<id>/` | WebSocket | Real-time chat |

---

## Deployment

### Backend (Production)

1. Set `DEBUG=False`
2. Configure PostgreSQL database
3. Configure Redis for channel layers
4. Set `ALLOWED_HOSTS` to your domain
5. Configure HTTPS (reverse proxy with nginx)
6. Run migrations
7. Create superuser
8. Seed initial rooms

### Client (Homebrew)

See [Homebrew Distribution](CLAUDE.md#part-3-homebrew-distribution) for building standalone binaries and creating a Homebrew tap.

---

## Project Structure

```
logographic-chat/
├── backend/                  # Django project
│   ├── logographic_chat/    # Django settings
│   ├── chat/                # Chat app (models, views, websockets)
│   ├── accounts/            # Auth app (device flow)
│   └── requirements.txt
├── client/                   # TUI client
│   ├── src/logographic_chat/
│   │   ├── auth.py         # Device auth
│   │   ├── api.py          # REST client
│   │   ├── ws.py           # WebSocket client
│   │   ├── tui.py          # Textual UI
│   │   └── cli.py          # CLI entry point
│   └── pyproject.toml
└── README.md
```
