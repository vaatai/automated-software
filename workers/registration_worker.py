"""Registration task worker with retry policies, exponential backoff,
worker isolation, proxy assignment, and structured task logging.

Each task runs in a fully isolated environment:
  - Dedicated asyncio event loop
  - Dedicated BrowserManager with single context
  - Isolated browser session (cookies, storage, fingerprint)
  - Per-task proxy assignment from pool
  - Structured logging to task_logs table
"""

import asyncio
import json
import logging
import time
from datetime import date, datetime, timezone

from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session, sessionmaker

from configs.celery_app import celery_app
from configs.settings import settings
from models.daily_limit import DailyLimit
from models.proxy import Proxy, ProxyStatus
from models.registration import Registration, RegistrationStatus
from models.task_log import LogLevel, TaskLog
from models.website import Website
from playwright_bot.browser_manager import BrowserManager
from playwright_bot.registration_bot import RegistrationBot

logger = logging.getLogger(__name__)

_engine = create_engine(settings.DATABASE_URL_SYNC, pool_pre_ping=True)
SyncSession = sessionmaker(bind=_engine)

# ── retry backoff config ────────────────────────────────────
MAX_RETRIES = 3
RETRY_BACKOFF = 30  # base delay in seconds
RETRY_BACKOFF_MAX = 300  # max delay cap
RETRY_JITTER = True


def _get_db() -> Session:
    return SyncSession()


def _log_task_event(
    db: Session,
    registration_id: int,
    celery_task_id: str | None,
    level: LogLevel,
    step: str,
    message: str,
    details: str | None = None,
    duration_ms: int | None = None,
) -> None:
    """Write a structured event to the task_logs table."""
    db.add(
        TaskLog(
            registration_id=registration_id,
            celery_task_id=celery_task_id,
            level=level,
            step=step,
            message=message,
            details=details,
            duration_ms=duration_ms,
        )
    )
    db.flush()


def _update_daily_count(db: Session, website_id: int, *, success: bool) -> None:
    today = date.today()
    daily = db.execute(
        select(DailyLimit).where(
            DailyLimit.website_id == website_id,
            DailyLimit.date == today,
        )
    ).scalar_one_or_none()

    if daily:
        daily.registration_count += 1
        if success:
            daily.success_count += 1
        else:
            daily.failure_count += 1
    else:
        db.add(
            DailyLimit(
                website_id=website_id,
                date=today,
                registration_count=1,
                success_count=1 if success else 0,
                failure_count=0 if success else 1,
            )
        )


def _assign_proxy(db: Session) -> Proxy | None:
    """Pick the least-recently-used active proxy from the pool."""
    proxy = db.execute(
        select(Proxy)
        .where(Proxy.status == ProxyStatus.ACTIVE, Proxy.deleted_at.is_(None))
        .order_by(Proxy.last_used_at.asc().nulls_first())
        .limit(1)
    ).scalar_one_or_none()

    if proxy:
        proxy.last_used_at = datetime.now(timezone.utc)
        db.flush()
    return proxy


# ── main registration task ──────────────────────────────────
@celery_app.task(
    bind=True,
    name="workers.registration_worker.execute_registration",
    max_retries=MAX_RETRIES,
    default_retry_delay=RETRY_BACKOFF,
    autoretry_for=(Exception,),
    retry_backoff=RETRY_BACKOFF,
    retry_backoff_max=RETRY_BACKOFF_MAX,
    retry_jitter=RETRY_JITTER,
    acks_late=True,
    reject_on_worker_lost=True,
    track_started=True,
    soft_time_limit=300,
    time_limit=600,
)
def execute_registration(self, registration_id: int, website_id: int) -> dict:
    """Run a single registration in a fully isolated browser context.

    Retry policy: exponential backoff (30s base, 300s cap) with jitter.
    Worker isolation: separate event loop, BrowserManager, proxy, cookies.
    """
    db = _get_db()
    task_id = self.request.id
    start_time = time.monotonic()

    try:
        # Load website config
        website = db.execute(
            select(Website).where(Website.id == website_id)
        ).scalar_one_or_none()
        if not website:
            raise ValueError(f"Website {website_id} not found")

        # Mark IN_PROGRESS
        db.execute(
            update(Registration)
            .where(Registration.id == registration_id)
            .values(
                status=RegistrationStatus.IN_PROGRESS,
                celery_task_id=task_id,
                started_at=datetime.now(timezone.utc),
                retry_count=self.request.retries,
            )
        )
        db.commit()

        _log_task_event(
            db, registration_id, task_id,
            LogLevel.INFO, "task_start",
            f"Registration started (attempt {self.request.retries + 1}/{MAX_RETRIES + 1})",
        )

        # Assign proxy from pool
        proxy = _assign_proxy(db)
        proxy_config = None
        if proxy:
            proxy_config = {"server": proxy.url}
            db.execute(
                update(Registration)
                .where(Registration.id == registration_id)
                .values(proxy_id=proxy.id)
            )
            _log_task_event(
                db, registration_id, task_id,
                LogLevel.INFO, "proxy_assigned",
                f"Proxy assigned: {proxy.host}:{proxy.port}",
            )
        db.commit()

        # Run registration in isolated event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                _run_isolated_registration(
                    website_config={
                        "url": website.url,
                        "form_config": website.form_config,
                    },
                    registration_id=registration_id,
                    requires_email_otp=website.requires_email_otp,
                    requires_mobile_otp=website.requires_mobile_otp,
                    proxy_config=proxy_config,
                )
            )
        finally:
            loop.close()

        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        # Update registration result
        ok = result["status"] == "completed"
        values: dict = {
            "status": RegistrationStatus.COMPLETED if ok else RegistrationStatus.FAILED,
            "email_used": result.get("email_used"),
            "phone_used": result.get("phone_used"),
            "username": result.get("username"),
            "email_otp_verified": result.get("email_otp_verified", False),
            "mobile_otp_verified": result.get("mobile_otp_verified", False),
            "error_message": result.get("error"),
            "screenshot_path": result.get("screenshot"),
        }
        if ok:
            values["completed_at"] = datetime.now(timezone.utc)

        db.execute(
            update(Registration)
            .where(Registration.id == registration_id)
            .values(**values)
        )
        _update_daily_count(db, website_id, success=ok)

        _log_task_event(
            db, registration_id, task_id,
            LogLevel.INFO if ok else LogLevel.WARNING,
            "task_complete",
            f"Registration {'completed' if ok else 'failed'}",
            details=json.dumps(result, default=str),
            duration_ms=elapsed_ms,
        )

        # Update proxy stats
        if proxy:
            if ok:
                proxy.success_count += 1
            else:
                proxy.fail_count += 1

        db.commit()
        return result

    except SoftTimeLimitExceeded:
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        db.execute(
            update(Registration)
            .where(Registration.id == registration_id)
            .values(
                status=RegistrationStatus.FAILED,
                error_message="Task exceeded soft time limit",
            )
        )
        _log_task_event(
            db, registration_id, task_id,
            LogLevel.ERROR, "timeout",
            "Task exceeded soft time limit (300s)",
            duration_ms=elapsed_ms,
        )
        _update_daily_count(db, website_id, success=False)
        db.commit()
        raise

    except Exception as exc:
        retries_exhausted = self.request.retries >= self.max_retries
        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        if retries_exhausted:
            db.execute(
                update(Registration)
                .where(Registration.id == registration_id)
                .values(
                    status=RegistrationStatus.FAILED,
                    error_message=str(exc),
                )
            )
            _update_daily_count(db, website_id, success=False)

            _log_task_event(
                db, registration_id, task_id,
                LogLevel.ERROR, "task_failed_permanent",
                f"All {MAX_RETRIES + 1} attempts exhausted",
                details=str(exc),
                duration_ms=elapsed_ms,
            )
            db.commit()

            # Send to dead-letter queue for inspection
            _send_to_dead_letter(registration_id, website_id, str(exc))

            logger.exception(
                "Registration %d permanently failed after %d attempts",
                registration_id,
                MAX_RETRIES + 1,
            )
            raise

        _log_task_event(
            db, registration_id, task_id,
            LogLevel.WARNING, "task_retry",
            f"Retrying (attempt {self.request.retries + 1}/{MAX_RETRIES + 1}): {exc}",
            duration_ms=elapsed_ms,
        )
        db.rollback()
        raise

    finally:
        db.close()


# ── priority variants ───────────────────────────────────────
@celery_app.task(
    bind=True,
    name="workers.registration_worker.execute_registration_high",
    max_retries=MAX_RETRIES,
    autoretry_for=(Exception,),
    retry_backoff=RETRY_BACKOFF,
    retry_backoff_max=RETRY_BACKOFF_MAX,
    retry_jitter=RETRY_JITTER,
    acks_late=True,
    reject_on_worker_lost=True,
    track_started=True,
    priority=2,
)
def execute_registration_high(
    self, registration_id: int, website_id: int
) -> dict:
    """High-priority registration (queue: registrations.high)."""
    return execute_registration(registration_id, website_id)


@celery_app.task(
    bind=True,
    name="workers.registration_worker.execute_registration_low",
    max_retries=MAX_RETRIES,
    autoretry_for=(Exception,),
    retry_backoff=RETRY_BACKOFF,
    retry_backoff_max=RETRY_BACKOFF_MAX,
    retry_jitter=RETRY_JITTER,
    acks_late=True,
    reject_on_worker_lost=True,
    track_started=True,
    priority=8,
)
def execute_registration_low(
    self, registration_id: int, website_id: int
) -> dict:
    """Low-priority registration (queue: registrations.low)."""
    return execute_registration(registration_id, website_id)


# ── async registration runner ───────────────────────────────
async def _run_isolated_registration(
    website_config: dict,
    registration_id: int,
    requires_email_otp: bool,
    requires_mobile_otp: bool,
    proxy_config: dict | None = None,
) -> dict:
    """Run a registration in a fully isolated async context.

    Creates a dedicated BrowserManager with:
    - Single browser context (max_contexts=1)
    - Isolated cookies and storage
    - Per-task proxy
    - Headless mode
    """
    mgr = BrowserManager(
        max_contexts=1,
        headless=True,
        default_timeout_ms=settings.OTP_POLL_TIMEOUT_SECONDS * 1000,
        navigation_timeout_ms=30_000,
        proxy=proxy_config,
    )
    await mgr.start()
    try:
        bot = RegistrationBot(browser_manager=mgr)
        return await bot.register(
            website_config=website_config,
            registration_id=registration_id,
            requires_email_otp=requires_email_otp,
            requires_mobile_otp=requires_mobile_otp,
        )
    finally:
        await mgr.stop()


# ── dead-letter sender ──────────────────────────────────────
def _send_to_dead_letter(
    registration_id: int, website_id: int, error: str
) -> None:
    """Forward permanently failed tasks to the dead-letter queue."""
    from workers.dead_letter_worker import process_dead_letter

    process_dead_letter.apply_async(
        kwargs={
            "registration_id": registration_id,
            "website_id": website_id,
            "error": error,
            "failed_at": datetime.now(timezone.utc).isoformat(),
        },
        queue="dead_letter",
    )


# ── scheduled tasks ─────────────────────────────────────────
@celery_app.task(name="workers.registration_worker.reset_daily_counters")
def reset_daily_counters() -> None:
    logger.info("Daily counters auto-reset via date-based tracking")
