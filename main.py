import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.daily_limits import router as daily_limits_router
from api.dashboard import router as dashboard_router
from api.health import router as health_router
from api.monitoring import router as monitoring_router
from api.proxies import router as proxies_router
from api.registrations import router as registrations_router
from api.tasks import router as tasks_router
from api.webhooks import router as webhooks_router
from api.websites import router as websites_router
from configs.settings import settings
from utils.logging_middleware import LoggingMiddleware

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Automated website registration with email OTP (MailSlurp) "
        "and mobile OTP (5SIM / PVAPins) verification."
    ),
    version=settings.APP_VERSION,
)

# ── middleware ──────────────────────────────────────────────
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── static files ───────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")

# ── routes ─────────────────────────────────────────────────
app.include_router(health_router)
app.include_router(dashboard_router)
app.include_router(websites_router)
app.include_router(registrations_router)
app.include_router(daily_limits_router)
app.include_router(tasks_router)
app.include_router(proxies_router)
app.include_router(monitoring_router)
app.include_router(webhooks_router)
