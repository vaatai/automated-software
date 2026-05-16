"""Proxy pool maintenance tasks — scheduled health checks, rate-limit resets,
and ban recovery.

Celery beat schedule:
  - reset-rate-limited-proxies: every 5 minutes
  - check-proxy-health: every 10 minutes (marks unhealthy proxies)
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session, sessionmaker

from configs.celery_app import celery_app
from configs.settings import settings
from models.proxy import Proxy, ProxyStatus
from services.proxy_manager import ProxyManager

logger = logging.getLogger(__name__)

_engine = create_engine(settings.DATABASE_URL_SYNC, pool_pre_ping=True)
SyncSession = sessionmaker(bind=_engine)


@celery_app.task(name="workers.proxy_worker.reset_rate_limited_proxies")
def reset_rate_limited_proxies() -> dict:
    """Reset all RATE_LIMITED proxies back to ACTIVE.

    Runs on schedule so that rate-limited proxies are automatically
    eligible for use again after the cooldown period.
    """
    db: Session = SyncSession()
    try:
        mgr = ProxyManager(db)
        count = mgr.reset_rate_limited_proxies()
        db.commit()
        logger.info("Reset %d rate-limited proxies", count)
        return {"reset_count": count}
    finally:
        db.close()


@celery_app.task(name="workers.proxy_worker.check_proxy_health")
def check_proxy_health() -> dict:
    """Periodic health check: deactivate proxies idle for too long
    or with zero success after many attempts.
    """
    db: Session = SyncSession()
    try:
        # Find proxies that have been ACTIVE but have high failure rates
        proxies = db.execute(
            select(Proxy).where(
                Proxy.status == ProxyStatus.ACTIVE,
                Proxy.deleted_at.is_(None),
                (Proxy.success_count + Proxy.fail_count) >= 10,
            )
        ).scalars().all()

        deactivated = 0
        for proxy in proxies:
            total = proxy.success_count + proxy.fail_count
            if total == 0:
                continue
            fail_rate = (proxy.fail_count / total) * 100
            if fail_rate > settings.PROXY_MAX_FAIL_RATE_PCT:
                proxy.status = ProxyStatus.INACTIVE
                deactivated += 1
                logger.warning(
                    "Proxy %d (%s:%d) deactivated: %.0f%% failure rate",
                    proxy.id, proxy.host, proxy.port, fail_rate,
                )

        # Mark stale RATE_LIMITED proxies (>30 min old) as ACTIVE
        stale_cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
        result = db.execute(
            update(Proxy)
            .where(
                Proxy.status == ProxyStatus.RATE_LIMITED,
                Proxy.last_used_at < stale_cutoff,
            )
            .values(status=ProxyStatus.ACTIVE)
        )
        recovered = result.rowcount

        db.commit()
        logger.info(
            "Health check: deactivated=%d, recovered=%d", deactivated, recovered
        )
        return {"deactivated": deactivated, "recovered": recovered}
    finally:
        db.close()
