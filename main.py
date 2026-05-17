import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.auth import router as auth_router
from api.daily_limits import router as daily_limits_router
from api.dashboard import router as dashboard_router
from api.health import router as health_router
from api.monitoring import router as monitoring_router
from api.proxies import router as proxies_router
from api.registrations import router as registrations_router
from api.tasks import router as tasks_router
from api.webhooks import router as webhooks_router
from api.websites import router as websites_router
from configs.celery_app import celery_app
from configs.settings import settings
from security.celery_security import apply_celery_security
from security.https_config import SecurityHeadersMiddleware
from security.scrubber import SensitiveFilter
from utils.logging_middleware import LoggingMiddleware

# ── logging setup with secret scrubbing ─────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
# Attach secret-scrubbing filter to root logger
root_logger = logging.getLogger()
for handler in root_logger.handlers:
    handler.addFilter(SensitiveFilter())

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Automated website registration with email OTP (MailSlurp) "
        "and mobile OTP (5SIM / PVAPins) verification."
    ),
    version=settings.APP_VERSION,
)

# ── middleware (order matters: first added = outermost) ─────
app.add_middleware(LoggingMiddleware)

# Security headers (HSTS, CSP, X-Frame-Options, etc.)
if settings.SECURITY_HEADERS_ENABLED:
    app.add_middleware(
        SecurityHeadersMiddleware,
        enable_hsts=settings.ENABLE_HSTS,
        enable_csp=settings.ENABLE_CSP,
    )

# CORS — use configured origins instead of wildcard in production
origins = [o.strip() for o in settings.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── static files ───────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")

# ── routes ─────────────────────────────────────────────────
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(websites_router)
app.include_router(registrations_router)
app.include_router(daily_limits_router)
app.include_router(tasks_router)
app.include_router(proxies_router)
app.include_router(monitoring_router)
app.include_router(webhooks_router)

# ── Celery security hardening ──────────────────────────────
apply_celery_security(celery_app, redis_ssl=settings.CELERY_REDIS_SSL)
