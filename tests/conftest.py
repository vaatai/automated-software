"""Shared test fixtures for the automated-software test suite."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Set test env vars before any app imports
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///test.db")
os.environ.setdefault("DATABASE_URL_SYNC", "sqlite:///test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")
os.environ.setdefault("MAILSLURP_API_KEY", "test-mailslurp-key")
os.environ.setdefault("FIVESIM_API_KEY", "test-fivesim-key")
os.environ.setdefault("PVAPINS_API_KEY", "test-pvapins-key")
os.environ.setdefault("SMSACTIVATE_API_KEY", "test-smsactivate-key")
os.environ.setdefault("DEBUG", "true")


# ── create test database tables ────────────────────────────────
def _create_tables():
    """Create all tables in the test SQLite DB."""
    import asyncio

    from sqlalchemy.ext.asyncio import create_async_engine

    import models  # noqa: F401 — registers all models with Base.metadata
    from configs.database import Base  # noqa: F401

    async def _init():
        engine = create_async_engine(os.environ["DATABASE_URL"])
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(_init())


_create_tables()


# ── application fixtures ───────────────────────────────────────


@pytest.fixture
def app():
    """Create a fresh FastAPI app instance with mocked external deps."""
    with patch("security.rate_limiter.RateLimiter.check", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = (True, {"limit": 100, "remaining": 99, "reset": 60})
        from main import app

        yield app


@pytest.fixture
def client(app):
    """Synchronous test client for API endpoint tests."""
    return TestClient(app)


@pytest.fixture
def async_client(app):
    """Async test client using httpx."""
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# ── mock fixtures ──────────────────────────────────────────────


@pytest.fixture
def mock_db_session():
    """Mock async database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def mock_sync_db():
    """Mock synchronous database session (for Celery workers)."""
    session = MagicMock()
    session.execute = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.flush = MagicMock()
    session.add = MagicMock()
    session.query = MagicMock()
    return session


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = AsyncMock()
    redis.zrangebyscore = AsyncMock(return_value=[])
    redis.zremrangebyscore = AsyncMock()
    redis.zadd = AsyncMock()
    redis.zcard = AsyncMock(return_value=0)
    redis.expire = AsyncMock()
    return redis


@pytest.fixture
def mock_celery_app():
    """Mock Celery application."""
    app = MagicMock()
    app.send_task = MagicMock()
    app.control = MagicMock()
    app.conf = MagicMock()
    return app


# ── data fixtures ──────────────────────────────────────────────


@pytest.fixture
def sample_website_config():
    """Sample website profile configuration."""
    return {
        "name": "Test Website",
        "url": "https://example.com/register",
        "form_config": {
            "steps": [
                {
                    "fields": [
                        {
                            "name": "email",
                            "selector": "#email",
                            "type": "text",
                        },
                        {
                            "name": "password",
                            "selector": "#password",
                            "type": "text",
                        },
                    ],
                }
            ],
        },
        "otp_settings": {
            "requires_email_otp": True,
            "email_otp_selector": "#otp-input",
        },
    }


@pytest.fixture
def sample_user_data():
    """Sample user creation data."""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "TestPassword123!",
        "role": "viewer",
    }


@pytest.fixture
def sample_proxy_data():
    """Sample proxy data."""
    return {
        "host": "proxy.example.com",
        "port": 8080,
        "protocol": "http",
        "username": "proxyuser",
        "password": "proxypass",
        "country": "US",
    }
