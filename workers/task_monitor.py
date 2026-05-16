"""Task monitoring worker — detects stale tasks and provides queue health metrics.

Runs on the monitoring queue to avoid interfering with registration workers.
"""

import logging
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
