"""Task monitoring worker — detects stale tasks, monitors worker health,
provides queue health metrics, and auto-throttles on high RAM usage.

Runs on the monitoring queue to avoid interfering with registration workers.
"""

import logging
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, func, select, update
from sqlalchemy.orm import sessionmaker

from configs.celery_app import celery_app
from configs.settings import settings
from models.registration import Registration, RegistrationStatus
from models.task_log import LogLevel, TaskLog

logger = logging.getLogger(__name__)

_engine = create_engine(settings.DATABASE_URL_SYNC, pool_pre_ping=True)
SyncSession = sessionmaker(bind=_engine)

STALE_THRESHOLD_MINUTES = 15


@celery_app.task(
    name="workers.task_monitor.check_stale_tasks",
    queue="monitoring",
    max_retries=0,
)
def check_stale_tasks() -> dict:
    """Detect and mark stale IN_PROGRESS registrations.

    A task is considered stale if it's been IN_PROGRESS for longer
    than STALE_THRESHOLD_MINUTES without completing.
    """
    db = SyncSession()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=STALE_THRESHOLD_MINUTES)

        stale = db.execute(
            select(Registration).where(
                Registration.status == RegistrationStatus.IN_PROGRESS,
                Registration.started_at < cutoff,
            )
        ).scalars().all()

        stale_count = 0
        for reg in stale:
            db.execute(
                update(Registration)
                .where(Registration.id == reg.id)
                .values(
                    status=RegistrationStatus.FAILED,
                    error_message=f"Task stale after {STALE_THRESHOLD_MINUTES} minutes",
                )
            )
            db.add(
                TaskLog(
                    registration_id=reg.id,
                    celery_task_id=reg.celery_task_id,
                    level=LogLevel.ERROR,
                    step="stale_detection",
                    message=f"Marked as failed — stale for >{STALE_THRESHOLD_MINUTES}m",
                )
            )
            stale_count += 1

        if stale_count:
            db.commit()
            logger.warning("Marked %d stale registrations as failed", stale_count)

        # Gather queue metrics
        counts = dict(
            db.execute(
                select(Registration.status, func.count())
                .group_by(Registration.status)
            ).all()
        )

        result = {
            "stale_detected": stale_count,
            "status_counts": {k.value if hasattr(k, "value") else k: v for k, v in counts.items()},
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info("Task monitor: %s", result)
        return result

    except Exception:
        db.rollback()
        logger.exception("Task monitor check failed")
        raise
    finally:
        db.close()


RAM_THROTTLE_PERCENT = 85


def _get_memory_usage() -> dict:
    """Read system memory stats from /proc/meminfo (Linux only)."""
    try:
        with open("/proc/meminfo") as f:
            info = {}
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    info[parts[0].rstrip(":")] = int(parts[1])
            total_kb = info.get("MemTotal", 0)
            avail_kb = info.get("MemAvailable", 0)
            used_kb = total_kb - avail_kb
            pct = round(used_kb / total_kb * 100, 1) if total_kb else 0
            return {
                "total_mb": round(total_kb / 1024),
                "used_mb": round(used_kb / 1024),
                "available_mb": round(avail_kb / 1024),
                "percent": pct,
            }
    except Exception:
        return {"total_mb": 0, "used_mb": 0, "available_mb": 0, "percent": 0}


@celery_app.task(
    name="workers.task_monitor.check_worker_health",
    queue="monitoring",
    max_retries=0,
)
def check_worker_health() -> dict:
    """Monitor worker health: RAM usage, active tasks, auto-pause on high memory.

    If RAM usage exceeds RAM_THROTTLE_PERCENT, active registration workers
    are signaled to cancel prefetched tasks (preventing new work pickup).
    """
    mem = _get_memory_usage()
    throttled = False

    if mem["percent"] > RAM_THROTTLE_PERCENT:
        logger.warning(
            "RAM usage %.1f%% exceeds %d%% threshold — throttling workers",
            mem["percent"], RAM_THROTTLE_PERCENT,
        )
        try:
            celery_app.control.cancel_consumer(
                "registrations", reply=True, timeout=5.0
            )
            throttled = True
        except Exception as exc:
            logger.warning("Failed to cancel consumer: %s", exc)
    elif mem["percent"] < RAM_THROTTLE_PERCENT - 10:
        # Re-enable if we dropped below threshold
        try:
            celery_app.control.add_consumer(
                "registrations", reply=True, timeout=5.0
            )
        except Exception:
            pass

    # Gather worker info
    try:
        inspect = celery_app.control.inspect(timeout=5.0)
        active = inspect.active() or {}
        stats = inspect.stats() or {}
        worker_count = len(stats)
        active_tasks = sum(len(tasks) for tasks in active.values())
    except Exception:
        worker_count = 0
        active_tasks = 0

    result = {
        "memory": mem,
        "throttled": throttled,
        "worker_count": worker_count,
        "active_tasks": active_tasks,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    logger.info("Worker health: %s", result)
    return result
