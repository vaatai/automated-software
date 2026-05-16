"""Daily limit worker — midnight reset, overflow processing, and old record cleanup.

Scheduled tasks:
  - process_overflow_queue: runs at startup of each day to re-queue
    overflow registrations from previous day
  - cleanup_daily_records: runs weekly to prune old daily_limit rows
"""

import logging
from datetime import date

from sqlalchemy import create_engine, func, select, update
from sqlalchemy.orm import sessionmaker

from configs.celery_app import celery_app
from configs.settings import settings
from models.daily_limit import DailyLimit
from models.registration import Registration, RegistrationStatus
from models.website import Website

logger = logging.getLogger(__name__)

_engine = create_engine(settings.DATABASE_URL_SYNC, pool_pre_ping=True)
SyncSession = sessionmaker(bind=_engine)


@celery_app.task(
    name="workers.daily_limit_worker.process_overflow_queue",
    queue="monitoring",
    max_retries=2,
)
def process_overflow_queue() -> dict:
    """Re-queue overflow registrations from previous day.

    Finds all DAILY_LIMIT_REACHED registrations, checks if today's
    limits allow them, and dispatches them to the registration queue.
    """
    from workers.registration_worker import execute_registration

    db = SyncSession()
    try:
        # Get all overflow registrations grouped by website
        overflow = db.execute(
            select(Registration)
            .where(Registration.status == RegistrationStatus.DAILY_LIMIT_REACHED)
            .order_by(Registration.created_at.asc())
        ).scalars().all()

        if not overflow:
            logger.info("No overflow registrations to process")
            return {"processed": 0, "queued": 0, "still_overflow": 0}

        # Group by website
        by_website: dict[int, list[Registration]] = {}
        for reg in overflow:
            by_website.setdefault(reg.website_id, []).append(reg)

        total_queued = 0
        total_still_overflow = 0

        for website_id, regs in by_website.items():
            website = db.execute(
                select(Website).where(Website.id == website_id)
            ).scalar_one_or_none()
            if not website:
                continue

            # Check today's usage
            today_record = db.execute(
                select(DailyLimit).where(
                    DailyLimit.website_id == website_id,
                    DailyLimit.date == date.today(),
                )
            ).scalar_one_or_none()

            used = today_record.registration_count if today_record else 0
            remaining = max(0, website.max_registrations_per_day - used)
            can_queue = min(len(regs), remaining)

            # Queue what we can
            for reg in regs[:can_queue]:
                db.execute(
                    update(Registration)
                    .where(Registration.id == reg.id)
                    .values(status=RegistrationStatus.PENDING)
                )
                execute_registration.delay(reg.id, website_id)
                total_queued += 1

            total_still_overflow += len(regs) - can_queue

        db.commit()

        logger.info(
            "Overflow processing: queued=%d, still_overflow=%d",
            total_queued, total_still_overflow,
        )

        return {
            "processed": len(overflow),
            "queued": total_queued,
            "still_overflow": total_still_overflow,
        }

    except Exception:
        db.rollback()
        logger.exception("Overflow processing failed")
        raise
    finally:
        db.close()


@celery_app.task(
    name="workers.daily_limit_worker.cleanup_daily_records",
    queue="monitoring",
    max_retries=0,
)
def cleanup_daily_records(days_to_keep: int = 30) -> dict:
    """Delete daily limit records older than N days."""
    from datetime import timedelta

    db = SyncSession()
    try:
        cutoff = date.today() - timedelta(days=days_to_keep)
        result = db.execute(
            select(func.count())
            .select_from(DailyLimit)
            .where(DailyLimit.date < cutoff)
        )
        count = result.scalar_one()

        if count > 0:
            from sqlalchemy import delete
            db.execute(delete(DailyLimit).where(DailyLimit.date < cutoff))
            db.commit()
            logger.info("Cleaned up %d old daily limit records (before %s)", count, cutoff)

        return {"deleted": count, "cutoff_date": cutoff.isoformat()}

    except Exception:
        db.rollback()
        logger.exception("Daily limit cleanup failed")
        raise
    finally:
        db.close()
