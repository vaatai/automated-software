# Automated Registration Software

Production-ready automated website registration platform with email OTP (MailSlurp) and mobile OTP (5SIM / PVAPins) verification. Supports parallel processing via Celery, daily registration limits, and a real-time dashboard.

## Features

- **Browser Automation** — Playwright fills and submits registration forms on any website
- **Email OTP Verification** — MailSlurp creates disposable inboxes, polls for OTP codes
- **Mobile OTP Verification** — 5SIM (primary) + PVAPins (fallback) for SMS verification
- **Parallel Processing** — Celery workers run multiple registrations simultaneously
- **Daily Limits** — Configurable per-website daily registration caps
- **Registration-Only Mode** — Skip OTP for sites that don't require it
- **Dashboard** — Real-time web UI to manage websites, trigger registrations, view logs
- **Error Handling** — Automatic retries, screenshot capture on failure
- **Async Architecture** — async/await throughout (FastAPI, SQLAlchemy, httpx)

## Architecture

```
User → Dashboard UI → FastAPI → Celery Task Queue → Worker (Playwright Bot)
                                                       ├── MailSlurp (email OTP)
                                                       ├── 5SIM     (mobile OTP)
                                                       └── PVAPins  (backup SMS)
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI (Python 3.11+) |
| Task Queue | Celery + Redis |
| Database | PostgreSQL + SQLAlchemy (async) |
| Migrations | Alembic |
| Browser Automation | Playwright (Chromium) |
| Email OTP | MailSlurp |
| Mobile OTP | 5SIM (primary), PVAPins (backup) |
| Containerisation | Docker + docker-compose |

## Project Structure

```
automated-software/
├── api/                    # FastAPI route handlers
│   ├── dashboard.py        # Dashboard HTML routes
│   ├── health.py           # Health-check endpoint
│   ├── registrations.py    # Registration CRUD + queue
│   ├── schemas.py          # Pydantic request/response models
│   └── websites.py         # Website CRUD
├── configs/                # All configuration & connections
│   ├── celery_app.py       # Celery broker/backend setup
│   ├── database.py         # Async SQLAlchemy engine + session
│   ├── redis.py            # Async Redis client
│   └── settings.py         # Pydantic Settings (env vars)
├── models/                 # SQLAlchemy ORM models
│   ├── daily_limit.py
│   ├── otp_config.py
│   ├── registration.py
│   └── website.py
├── services/               # Business logic layer
│   └── registration_service.py
├── workers/                # Celery task definitions
│   └── registration_worker.py
├── playwright_bot/         # Playwright browser automation
│   └── registration_bot.py
├── otp/                    # OTP provider integrations
│   ├── base.py             # Abstract base + OTP extraction
│   ├── mailslurp_service.py
│   ├── fivesim_service.py
│   └── pvapins_service.py
├── utils/                  # Shared utilities
│   ├── data_generator.py   # Random user-data generator
│   └── logging_middleware.py
├── alembic/                # Database migrations
│   ├── env.py
│   └── versions/
├── templates/              # Jinja2 HTML templates
│   └── dashboard/
├── static/                 # CSS / JS assets
│   ├── css/
│   └── js/
├── main.py                 # FastAPI app entrypoint
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── pyproject.toml
├── .env.example
└── .gitignore
```

## Quick Start

### 1. Prerequisites

- Python 3.11+
- PostgreSQL
- Redis
- Docker (optional, recommended)

### 2. Clone & Install

```bash
git clone https://github.com/vaatai/automated-software.git
cd automated-software
pip install -r requirements.txt
playwright install chromium
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys and database credentials
```

**Required API keys:**

| Key | Provider |
|-----|----------|
| `MAILSLURP_API_KEY` | [MailSlurp](https://www.mailslurp.com/) |
| `FIVESIM_API_KEY` | [5SIM](https://5sim.net/) |
| `PVAPINS_API_KEY` | [PVAPins](https://pvapins.com/) (backup) |

### 4. Database Setup

```bash
createdb automated_software
alembic upgrade head
```

### 5. Start Services

**With Docker (recommended):**

```bash
docker compose up -d
```

**Without Docker:**

```bash
# Terminal 1 — Redis
redis-server

# Terminal 2 — FastAPI
uvicorn main:app --reload --port 8000

# Terminal 3 — Celery worker
celery -A configs.celery_app worker --loglevel=info --concurrency=5

# Terminal 4 — Celery beat (scheduled tasks)
celery -A configs.celery_app beat --loglevel=info
```

### 6. Open Dashboard

Navigate to **http://localhost:8000**

## API Endpoints

| Method | Endpoint | Description |
|--------|---------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/` | Dashboard UI |
| `POST` | `/api/websites/` | Add website |
| `GET` | `/api/websites/` | List websites |
| `GET` | `/api/websites/{id}` | Get website |
| `PUT` | `/api/websites/{id}` | Update website |
| `DELETE` | `/api/websites/{id}` | Delete website |
| `POST` | `/api/registrations/` | Queue registrations |
| `GET` | `/api/registrations/` | List registrations |
| `GET` | `/api/registrations/{id}` | Get registration |
| `GET` | `/api/registrations/stats/{website_id}` | Daily stats |
| `GET` | `/api/registrations/task/{task_id}` | Celery task status |

## Usage Example

### Add a Website

```bash
curl -X POST http://localhost:8000/api/websites/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Example Site",
    "url": "https://example.com",
    "form_config": {
      "registration_url": "https://example.com/register",
      "fields": {
        "email": {"selector": "#email", "type": "email"},
        "password": {"selector": "#password", "type": "password"},
        "username": {"selector": "#username", "type": "text"}
      },
      "submit_button": {"selector": "#submit-btn"},
      "success_indicator": {"selector": ".success-message"}
    },
    "requires_email_otp": true,
    "requires_mobile_otp": false,
    "max_registrations_per_day": 50
  }'
```

### Trigger Registrations

```bash
curl -X POST http://localhost:8000/api/registrations/ \
  -H "Content-Type: application/json" \
  -d '{"website_id": 1, "count": 5}'
```

## Registration Modes

| Mode | Email OTP | Mobile OTP | Use Case |
|------|-----------|------------|----------|
| Registration Only | No | No | Sites without verification |
| Email OTP | Yes | No | Email verification only |
| Mobile OTP | No | Yes | Phone verification only |
| Full Verification | Yes | Yes | Both verifications |

## License

MIT
