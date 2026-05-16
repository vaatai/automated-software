"""Dead-letter queue worker for permanently failed registration tasks.

Processes tasks that exhausted all retries to:
- Log the failure with full context
- Update registration status
- Optionally trigger alerts or notifications
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import sessionmaker

from configs.celery_app import celery_app
from configs.settings import settings
from models.registration import Registration, RegistrationStatus
from models.task_log import LogLevel, TaskLog

logger = logging.getLogger(__name__)

_engine = create_engine(settings.DATABASE_URL_SYNC, pool_pre_ping=True)
SyncSession = sessionmaker(bind=_engine)


@celery_app.task(
    name="workers.dead_letter_worker.process_dead_letter",
    queue="dead_letter",
    max_retries=0,
    acks_late=True,
)
def process_dead_letter(
    registration_id: int,
    website_id: int,
    error: str,
    failed_at: str | None = None,
) -> dict:
    """Process a permanently failed registration task.

    Logs the failure event and ensures the registration is marked as failed.
    """
    db = SyncSession()
    try:
        reg = db.execute(
            select(Registration).where(Registration.id == registration_id)
        ).scalar_one_or_none()

        if not reg:
            logger.warning("DLQ: registration %d not found", registration_id)
            return {"status": "not_found", "registration_id": registration_id}

        # Ensure it's marked FAILED
        if reg.status != RegistrationStatus.FAILED:
            db.execute(
                update(Registration)
                .where(Registration.id == registration_id)
                .values(
                    status=RegistrationStatus.FAILED,
                    error_message=error,
                )
            )

        # Log dead-letter event
        db.add(
            TaskLog(
                registration_id=registration_id,
                celery_task_id=reg.celery_task_id,
                level=LogLevel.CRITICAL,
                step="dead_letter",
                message="Task moved to dead-letter queue after all retries exhausted",
                details=error,
            )
        )
        db.commit()

        logger.error(
            "DLQ processed: registration=%d website=%d error=%s failed_at=%s",
            registration_id,
            website_id,
            error,
            failed_at or "unknown",
        )

        return {
            "status": "processed",
            "registration_id": registration_id,
            "website_id": website_id,
            "error": error,
            "failed_at": failed_at,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception:
        db.rollback()
        logger.exception("DLQ processing failed for registration %d", registration_id)
        raise
    finally:
        db.close()
