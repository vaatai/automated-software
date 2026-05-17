"""Registration task worker with retry policies, exponential backoff,
worker isolation, proxy assignment, and structured task logging.

Each task runs in a fully isolated environment:
  - Dedicated asyncio event loop
  - Dedicated BrowserManager with single context
  - Isolated browser session (cookies, storage, fingerprint)
  - Per-task proxy assignment from pool
  - Structured logging to task_logs table

Enhanced with centralized error handling:
  - Error classification (transient vs permanent, CAPTCHA, proxy ban, etc.)
  - Automatic proxy swapping on ban detection
  - Rich debugging context stored per failure
  - Category-aware retry decisions
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
from models.proxy import Proxy
from models.registration import Registration, RegistrationStatus
from models.task_log import LogLevel, TaskLog
from models.website import Website
from playwright_bot.browser_manager import BrowserManager
from playwright_bot.registration_bot import RegistrationBot
from services.proxy_manager import ProxyManager
from utils.error_handler import PROXY_SWAP_CATEGORIES, RETRIABLE_CATEGORIES, ErrorCategory

logger = logging.getLogger(__name__)

_engine = create_engine(settings.DATABASE_URL_SYNC, pool_pre_ping=True)
SyncSession = sessionmaker(bind=_engine)

# ── retry backoff config ────────────────────────────────────
MAX_RETRIES = 3
RETRY_BACKOFF = 30  # base delay in seconds
RETRY_BACKOFF_MAX = 300  # max delay cap
RETRY_JITTER = True

# Exceptions that should NOT be retried (permanent failures)
NON_RETRIABLE = (SoftTimeLimitExceeded, ValueError, KeyError, TypeError)

# Error categories that should not be retried
NON_RETRIABLE_CATEGORIES = frozenset(
    {
        ErrorCategory.PERMANENT,
        ErrorCategory.CAPTCHA_DETECTED,
        ErrorCategory.SELECTOR_CHANGED,
        ErrorCategory.BROWSER_CRASH,
    }
)


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
    screenshot_path: str | None = None,
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
            screenshot_path=screenshot_path,
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


def _assign_proxy(
    db: Session,
    country: str | None = None,
    exclude_ids: list[int] | None = None,
) -> Proxy | None:
    """Assign a proxy via ProxyManager with LRU rotation."""
    mgr = ProxyManager(db)
    if country:
        return mgr.assign_proxy_for_country(country, fallback=True)
    return mgr.assign_proxy(exclude_ids=exclude_ids)


def _classify_result_error(result: dict) -> ErrorCategory | None:
    """Extract error category from bot result's error_context."""
    error_ctx = result.get("error_context")
    if error_ctx and isinstance(error_ctx, dict):
        cat_str = error_ctx.get("category", "")
        try:
            return ErrorCategory(cat_str)
        except ValueError:
            pass
    return None


# ── shared registration logic (plain function, not a task) ──
def _do_registration(
    task,
    registration_id: int,
    website_id: int,
    failed_proxy_ids: list[int] | None = None,
) -> dict:
    """Core registration logic shared by all priority variants.

    Accepts the bound Celery task instance so that self.request.id,
    self.request.retries, and self.retry() work correctly regardless
    of which queue/priority variant dispatched the task.

    Retry policy:
    - Manual self.retry() with exponential backoff
    - Error category from ErrorHandler determines retry eligibility
    - Non-retriable exceptions (SoftTimeLimitExceeded, ValueError, etc.)
      are sent to the dead-letter queue immediately
    - CAPTCHA/selector-changed errors go to DLQ (need human intervention)
    - Proxy ban triggers proxy swap before retry

    Args:
        failed_proxy_ids: Proxy IDs that failed on previous attempts,
            passed through Celery retry kwargs to persist across retries.
    """
    db = _get_db()
    task_id = task.request.id
    start_time = time.monotonic()
    if failed_proxy_ids is None:
        failed_proxy_ids = []

    try:
        # Load website config
        website = db.execute(select(Website).where(Website.id == website_id)).scalar_one_or_none()
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
                retry_count=task.request.retries,
            )
        )
        db.commit()

        _log_task_event(
            db,
            registration_id,
            task_id,
            LogLevel.INFO,
            "task_start",
            f"Registration started (attempt {task.request.retries + 1}/{MAX_RETRIES + 1})",
        )

        # Assign proxy from pool (exclude previously failed proxies)
        proxy = _assign_proxy(db, exclude_ids=failed_proxy_ids or None)
        proxy_config = None
        if proxy:
            proxy_config = {"server": proxy.url}
            db.execute(
                update(Registration)
                .where(Registration.id == registration_id)
                .values(proxy_id=proxy.id)
            )
            _log_task_event(
                db,
                registration_id,
                task_id,
                LogLevel.INFO,
                "proxy_assigned",
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
                    attempt_number=task.request.retries + 1,
                )
            )
        finally:
            loop.close()

        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        # Extract error category from result
        error_category = _classify_result_error(result)

        # Update registration result
        ok = result["status"] == "completed"
        error_context = result.get("error_context")
        values: dict = {
            "status": RegistrationStatus.COMPLETED if ok else RegistrationStatus.FAILED,
            "email_used": result.get("email_used"),
            "phone_used": result.get("phone_used"),
            "username": result.get("username"),
            "email_otp_verified": result.get("email_otp_verified", False),
            "mobile_otp_verified": result.get("mobile_otp_verified", False),
            "error_message": result.get("error"),
            "screenshot_path": result.get("screenshot"),
            "html_snapshot_path": result.get("html_snapshot"),
            "browser_log_path": result.get("browser_log"),
            "error_category": error_category.value if error_category else None,
            "error_context": error_context,
        }
        if ok:
            values["completed_at"] = datetime.now(timezone.utc)

        db.execute(update(Registration).where(Registration.id == registration_id).values(**values))

        # Store detailed debugging info as task log
        details_json = json.dumps(result, default=str)

        if ok:
            _update_daily_count(db, website_id, success=True)
            _log_task_event(
                db,
                registration_id,
                task_id,
                LogLevel.INFO,
                "task_complete",
                "Registration completed successfully",
                details=details_json,
                duration_ms=elapsed_ms,
            )
        else:
            # Log the error with full context
            _log_task_event(
                db,
                registration_id,
                task_id,
                LogLevel.WARNING,
                "task_failed",
                f"Registration failed: {result.get('error', 'unknown')}",
                details=json.dumps(error_context, default=str) if error_context else details_json,
                duration_ms=elapsed_ms,
                screenshot_path=result.get("screenshot"),
            )

            # Category-specific handling
            if error_category and error_category in NON_RETRIABLE_CATEGORIES:
                _log_task_event(
                    db,
                    registration_id,
                    task_id,
                    LogLevel.ERROR,
                    "error_permanent",
                    f"Non-retriable error category: {error_category.value}",
                    details=json.dumps(error_context, default=str) if error_context else None,
                )
                _update_daily_count(db, website_id, success=False)
                db.commit()
                _send_to_dead_letter(
                    registration_id,
                    website_id,
                    f"[{error_category.value}] {result.get('error', 'unknown')}",
                )
                return result

            # Track proxy failures for swap on retry
            if proxy and error_category and error_category in PROXY_SWAP_CATEGORIES:
                proxy_mgr = ProxyManager(db)
                is_ban = error_category == ErrorCategory.PROXY_BAN
                is_rate = error_category == ErrorCategory.PROXY_RATE_LIMITED
                proxy_mgr.record_failure(
                    proxy.id,
                    error=result.get("error"),
                    is_ban=is_ban,
                    is_rate_limit=is_rate,
                )
                failed_proxy_ids.append(proxy.id)
                _log_task_event(
                    db,
                    registration_id,
                    task_id,
                    LogLevel.WARNING,
                    "proxy_failure",
                    f"Proxy {proxy.host}:{proxy.port} {'banned' if is_ban else 'rate-limited'}",
                )

        # Update proxy stats via ProxyManager
        if proxy and ok:
            proxy_mgr = ProxyManager(db)
            proxy_mgr.record_success(proxy.id)
        elif proxy and error_category not in (PROXY_SWAP_CATEGORIES if error_category else set()):
            proxy_mgr = ProxyManager(db)
            proxy_mgr.record_failure(proxy.id, error=result.get("error"))

        db.commit()

        # If the bot returned failure but it's retriable, raise to trigger Celery retry
        if not ok and error_category and error_category in RETRIABLE_CATEGORIES:
            retries_exhausted = task.request.retries >= task.max_retries
            if not retries_exhausted:
                _log_task_event(
                    db,
                    registration_id,
                    task_id,
                    LogLevel.WARNING,
                    "task_retry",
                    f"Retrying [{error_category.value}] "
                    f"(attempt {task.request.retries + 1}/{MAX_RETRIES + 1}): "
                    f"{result.get('error', 'unknown')}",
                    duration_ms=elapsed_ms,
                )
                db.commit()
                raise task.retry(
                    exc=Exception(result.get("error", "Retriable failure")),
                    kwargs={
                        "registration_id": registration_id,
                        "website_id": website_id,
                        "failed_proxy_ids": failed_proxy_ids,
                    },
                )
            else:
                _update_daily_count(db, website_id, success=False)
                _log_task_event(
                    db,
                    registration_id,
                    task_id,
                    LogLevel.ERROR,
                    "task_failed_permanent",
                    f"All {MAX_RETRIES + 1} attempts exhausted",
                    details=json.dumps(error_context, default=str) if error_context else None,
                    duration_ms=elapsed_ms,
                )
                db.commit()
                _send_to_dead_letter(
                    registration_id,
                    website_id,
                    result.get("error", "unknown"),
                )
                return result

        if not ok:
            _update_daily_count(db, website_id, success=False)
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
            db,
            registration_id,
            task_id,
            LogLevel.ERROR,
            "timeout",
            "Task exceeded soft time limit (300s)",
            duration_ms=elapsed_ms,
        )
        _update_daily_count(db, website_id, success=False)
        db.commit()
        _send_to_dead_letter(registration_id, website_id, "Soft time limit exceeded")
        raise

    except NON_RETRIABLE as exc:
        # Permanent failures — do not retry
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
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
            db,
            registration_id,
            task_id,
            LogLevel.ERROR,
            "task_failed_permanent",
            f"Non-retriable error: {type(exc).__name__}",
            details=str(exc),
            duration_ms=elapsed_ms,
        )
        db.commit()
        _send_to_dead_letter(registration_id, website_id, str(exc))
        logger.exception("Registration %d permanently failed (non-retriable)", registration_id)
        raise

    except Exception as exc:
        # Transient failures — retry with exponential backoff
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        retries_exhausted = task.request.retries >= task.max_retries

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
                db,
                registration_id,
                task_id,
                LogLevel.ERROR,
                "task_failed_permanent",
                f"All {MAX_RETRIES + 1} attempts exhausted",
                details=str(exc),
                duration_ms=elapsed_ms,
            )
            db.commit()
            _send_to_dead_letter(registration_id, website_id, str(exc))
            logger.exception(
                "Registration %d permanently failed after %d attempts",
                registration_id,
                MAX_RETRIES + 1,
            )
            raise

        # Log retry event and commit before re-raising
        _log_task_event(
            db,
            registration_id,
            task_id,
            LogLevel.WARNING,
            "task_retry",
            f"Retrying (attempt {task.request.retries + 1}/{MAX_RETRIES + 1}): {exc}",
            duration_ms=elapsed_ms,
        )
        db.commit()

        logger.warning(
            "Registration %d failed (retry %d/%d)",
            registration_id,
            task.request.retries + 1,
            task.max_retries,
        )
        raise task.retry(exc=exc)

    finally:
        db.close()


# ── celery task definitions ─────────────────────────────────
@celery_app.task(
    bind=True,
    name="workers.registration_worker.execute_registration",
    max_retries=MAX_RETRIES,
    default_retry_delay=RETRY_BACKOFF,
    retry_backoff=RETRY_BACKOFF,
    retry_backoff_max=RETRY_BACKOFF_MAX,
    retry_jitter=RETRY_JITTER,
    throws=(SoftTimeLimitExceeded, ValueError),
    acks_late=True,
    reject_on_worker_lost=True,
    track_started=True,
    soft_time_limit=300,
    time_limit=600,
)
def execute_registration(
    self,
    registration_id: int,
    website_id: int,
    failed_proxy_ids: list[int] | None = None,
) -> dict:
    """Normal-priority registration (queue: registrations)."""
    return _do_registration(self, registration_id, website_id, failed_proxy_ids)


@celery_app.task(
    bind=True,
    name="workers.registration_worker.execute_registration_high",
    max_retries=MAX_RETRIES,
    default_retry_delay=RETRY_BACKOFF,
    retry_backoff=RETRY_BACKOFF,
    retry_backoff_max=RETRY_BACKOFF_MAX,
    retry_jitter=RETRY_JITTER,
    throws=(SoftTimeLimitExceeded, ValueError),
    acks_late=True,
    reject_on_worker_lost=True,
    track_started=True,
    soft_time_limit=300,
    time_limit=600,
    priority=2,
)
def execute_registration_high(
    self,
    registration_id: int,
    website_id: int,
    failed_proxy_ids: list[int] | None = None,
) -> dict:
    """High-priority registration (queue: registrations.high)."""
    return _do_registration(self, registration_id, website_id, failed_proxy_ids)


@celery_app.task(
    bind=True,
    name="workers.registration_worker.execute_registration_low",
    max_retries=MAX_RETRIES,
    default_retry_delay=RETRY_BACKOFF,
    retry_backoff=RETRY_BACKOFF,
    retry_backoff_max=RETRY_BACKOFF_MAX,
    retry_jitter=RETRY_JITTER,
    throws=(SoftTimeLimitExceeded, ValueError),
    acks_late=True,
    reject_on_worker_lost=True,
    track_started=True,
    soft_time_limit=300,
    time_limit=600,
    priority=8,
)
def execute_registration_low(
    self,
    registration_id: int,
    website_id: int,
    failed_proxy_ids: list[int] | None = None,
) -> dict:
    """Low-priority registration (queue: registrations.low)."""
    return _do_registration(self, registration_id, website_id, failed_proxy_ids)


# ── async registration runner ───────────────────────────────
async def _run_isolated_registration(
    website_config: dict,
    registration_id: int,
    requires_email_otp: bool,
    requires_mobile_otp: bool,
    proxy_config: dict | None = None,
    attempt_number: int = 1,
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
            attempt_number=attempt_number,
        )
    finally:
        await mgr.stop()


# ── dead-letter sender ──────────────────────────────────────
def _send_to_dead_letter(registration_id: int, website_id: int, error: str) -> None:
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
def reset_daily_counters() -> dict:
    """Reset daily counters — called by Celery beat at midnight."""
    logger.info("Daily counter reset triggered")
    return {"status": "ok", "reset_at": datetime.now(timezone.utc).isoformat()}
